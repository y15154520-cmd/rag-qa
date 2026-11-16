"""
步骤 3：检索 + 生成。问一个问题 → 从 Chroma 找出最相关的 3 条 → 拼进 prompt → 让模型回答并标出依据。

验收：
    - 问 "怎么请年假？"：回答里引用了第四十五条
    - 问一个检索结果里答不了的问题：回答是 "在检索到的条款中没有找到相关规定"，没有编造
"""

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import Text2VecEmbeddingFunction

from llm import call_llm

DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "labor_law"


def build_collection():
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=Text2VecEmbeddingFunction())
    return collection

def search(collection, question, k=8, fetch_n=50):
    """问一个问题，返回最相近的 k 块。"""

    raw = collection.query(
        query_texts=[question],
        n_results=fetch_n
    )
    seen = set()
    ids, metadatas, documents, distances = [], [], [], []
    for id_, meta, doc, dist in zip(raw['ids'][0], raw['metadatas'][0], raw['documents'][0], raw['distances'][0]):
        key = (meta.get('law'), meta.get('article'))
        if key in seen:
            continue
        seen.add(key)
        ids.append(id_)
        metadatas.append(meta)
        documents.append(doc)
        distances.append(dist)
        if len(ids) >= k:
            break
    results = {
        'ids': [ids],
        'metadatas': [metadatas],
        'documents': [documents],
        'distances': [distances]
    }
    return results


def rewrite_query(question):
    """
    TODO（问题改写）：把用户的大白话改写成法条里会出现的说法。

    例：
        "公司一直不跟我签合同，我能要求什么赔偿？"
        → "用人单位未与劳动者订立书面劳动合同，应当支付二倍的工资"

    要回答的问题（先口述再写）：
      1. prompt 里要写清楚哪几件事？（至少：要它做什么 / 范围是劳动法规 / 只输出一句话、不要解释）
      2. 要不要在 prompt 里给一两个"原话 → 改写"的例子？给的话，例子能不能用评测集里的题？
         （提示：用评测题当例子 = 考试前把答案告诉它，分数会虚高）
      3. 模型返回的文字，要不要 .strip()？万一它还是加了引号或"改写："，怎么办？
    """
    prompt = (
        "你是中国劳动法规方面的检索助手。请把用户的口语化问题，改写成《劳动法》《劳动合同法》"
        "《职工带薪年休假条例》这类法条原文里会出现的说法，用来在法条库里做检索。\n"
        "要求：\n"
        "1. 用法条里的术语，比如“公司”说成“用人单位”，“我/员工”说成“劳动者”或“职工”；\n"
        "2. 写成一句陈述句，不要写成问句；\n"
        "3. 只输出改写后的这一句话，不要解释，不要加引号，不要加“改写：”之类的前缀。\n\n"
        "例子：\n"
        "原话：公司扣着我的身份证不还，合法吗？\n"
        "改写：用人单位招用劳动者，不得扣押劳动者的居民身份证和其他证件\n"
        "原话：女员工生完孩子能休多久？\n"
        "改写：女职工生育享受不少于九十天的产假\n\n"
        f"原话：{question}\n"
        "改写："
    )
    try:
        text = call_llm(prompt, max_tokens=2000)
    except Exception as e:
        print(f"[改写失败，用原话检索] {e}")
        return question

    text = text.strip().splitlines()[0].strip()
    for prefix in ("改写后：", "改写：", "改写后:", "改写:"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    text = text.strip("\"'“”‘’「」『』")
    return text or question


def search_with_rewrite(collection, question, k=8, fetch_n=50, per_query_k=8):
    """
    TODO（问题改写）：原话和改写各检索一次，合并成 k 条。

    要回答的问题（先口述再写）：
      1. 两次检索各拿回一份结果，同一条法条可能两份里都有，距离不一样 —— 保留哪个？
      2. 合并以后按什么排序？排完取前 k 条
      3. 返回值还要保持 search 的样子（ids / metadatas / documents / distances，外面套一层列表）
      4. 调试用：把改写后的句子打印出来，不然你不知道它到底改成了什么
    """
    rewritten = rewrite_query(question)
    print(f"[改写] {question} → {rewritten}")
    merged = {}
    for q in (question, rewritten):
        r = search(collection, q, k=per_query_k, fetch_n=fetch_n)
        for rank, (id_, meta, doc, dist) in enumerate(
            zip(r['ids'][0], r['metadatas'][0], r['documents'][0], r['distances'][0]), start=1
        ):
            key = (meta.get('law'), meta.get('article'))
            if key not in merged:
                merged[key] = {'id': id_, 'meta': meta, 'doc': doc, 'dist': dist,
                               'best_rank': rank, 'hits': 0}
            elif dist < merged[key]['dist']:
                merged[key].update(id=id_, meta=meta, doc=doc, dist=dist)
            merged[key]['best_rank'] = min(merged[key]['best_rank'], rank)
            merged[key]['hits'] += 1

    top = sorted(merged.values(), key=lambda x: (x['best_rank'], -x['hits']))[:k]
    return {
        'ids': [[t['id'] for t in top]],
        'metadatas': [[t['meta'] for t in top]],
        'documents': [[t['doc'] for t in top]],
        'distances': [[t['dist'] for t in top]],
        'scores': [[t['best_rank'] for t in top]],
    }


def make_label(meta):
    """把 meta 里的 law / chapter / section / article 拼成一个标签。"""
    parts = [f"《{meta['law']}》", meta.get('chapter'), meta.get('section'), meta.get('article')]
    label = " ".join([p for p in parts if p])
    return label
def build_prompt(question, results):
    prompt = f"请根据以下资料回答问题：\n\n"
    for i in range(len(results['documents'][0])):
        chapter = results['metadatas'][0][i].get('chapter')
        article = results['metadatas'][0][i].get('article')
        section = results['metadatas'][0][i].get('section')
        content = results['metadatas'][0][i].get('article_text')
        law = results['metadatas'][0][i].get('law')
        label = make_label(results['metadatas'][0][i])
        prompt += f"【{label}】{content}\n\n"
    prompt += f"问题：{question}\n\n"
    prompt += "用自然、口语化的一段话回答，像在跟同事解释一样，不要使用“依据”“结论”这类小标题并且在同一语境下不要重复说一些内容，能让人听明白是什么即可。请只根据以上资料回答问题，不要使用你自己的知识，如果资料能完整回答，则先写依据，再写结论；如果资料只能回答一部分，则写出能回答的部分和依据，再明确说出资料里没有的是哪一部分；如果在检索到的条款中没有找到相关规定，则请直接回答“在检索到的条款中没有找到相关规定”，不要猜测，不要补充。回答的最后另起一行，写：依据：《XXXXX》第X章，X条，比如“依据：《劳动法》第四章 第四十五条”，再比如“依据：《职工带薪年休假条例》第三条”。回答里提到资料时，用“我查到的相关条款”这类说法，不要出现“资料”两个字。资料没覆盖的部分，固定建议一句“建议咨询单位人事部门”。"
    return prompt


if __name__ == "__main__":
    collection = build_collection()
    while True:
        question = input("请输入问题（输入 exit 或 quit 退出）：")
        if question ==  '':
            continue
        if question.lower() in ['exit', 'quit']:
            break
        results = search_with_rewrite(collection, question)
        # 调试：看看检索回来的是哪几条
        print(f"--- 检索到 {len(results['ids'][0])} 条 ---")
        print("距离    法律  条    最好名次")
        for meta, dist, best_rank in zip(results['metadatas'][0], results['distances'][0], results['scores'][0]):
            print(f"{dist:.4f}  {meta.get('law')}  {meta.get('article')}  第 {best_rank} 名")
        print("---")
        prompt = build_prompt(question, results)
        print(call_llm(prompt))

