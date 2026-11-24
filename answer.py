"""
检索 + 生成：问一个问题 → 从 Chroma 检索最相关的 8 条法条 → 拼进 prompt → 让模型回答并标出依据。

命令行问答（会打印检索到的法条和距离，方便核对回答的依据）：
    python answer.py
"""

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import Text2VecEmbeddingFunction

from llm import call_llm

DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "labor_law"


def build_collection():
    """打开 build_index.py 建好的向量库（同时加载中文 embedding 模型）。"""
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=Text2VecEmbeddingFunction())
    return collection


def search(collection, question, k=8, fetch_n=50):
    """
    检索 k 条不同的法条。

    一条长法条按项拆成了几块，可能一条占好几个名额，所以先多取 fetch_n 块，
    同一条（法名 + 条号）只留排得最靠前的一块，凑够 k 条就停。
    返回值的结构和 collection.query 一样（每个字段外面套一层列表）。
    """

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


def make_label(meta):
    """把 meta 里的 law / chapter / section / article 拼成一个标签。"""
    parts = [f"《{meta['law']}》", meta.get('chapter'), meta.get('section'), meta.get('article')]
    label = " ".join([p for p in parts if p])
    return label


def build_prompt(question, results):
    """把检索到的每条法条（标签 + 整条原文）和回答规则拼成 prompt。"""
    prompt = f"请根据以下资料回答问题：\n\n"
    for i in range(len(results['documents'][0])):
        content = results['metadatas'][0][i]['article_text']  # 缺了就报错，别让 None 混进 prompt
        label = make_label(results['metadatas'][0][i])
        prompt += f"【{label}】{content}\n\n"
    prompt += f"问题：{question}\n\n"
    prompt += "用自然、口语化的一段话回答，像在跟同事解释一样，不要使用“依据”“结论”这类小标题并且在同一语境下不要重复说一些内容，能让人听明白是什么即可。请只根据以上资料回答问题，不要使用你自己的知识，如果资料能完整回答，则先写依据，再写结论；如果资料只能回答一部分，则写出能回答的部分和依据，再明确说出资料里没有的是哪一部分；如果在检索到的条款中没有找到相关规定，则请直接回答“在检索到的条款中没有找到相关规定”，不要猜测，不要补充。回答的最后另起一行，写：依据：《XXXXX》第X章，X条，比如“依据：《劳动法》第四章 第四十五条”，再比如“依据：《职工带薪年休假条例》第三条”。回答里提到资料时，用“我查到的相关条款”这类说法，不要出现“资料”两个字。资料没覆盖的部分，固定建议一句“建议咨询单位人事部门”。"
    return prompt


if __name__ == "__main__":
    collection = build_collection()
    while True:
        question = input("请输入问题（输入 exit 或 quit 退出）：")
        if question == '':
            continue
        if question.lower() in ['exit', 'quit']:
            break
        results = search(collection, question)
        # 打印检索结果，方便核对回答依据了哪几条
        print(f"--- 检索到 {len(results['ids'][0])} 条 ---")
        for meta, dist in zip(results['metadatas'][0], results['distances'][0]):
            print(f"{dist:.4f}  {meta.get('law')}  {meta.get('article')}")
        print("---")
        prompt = build_prompt(question, results)
        print(call_llm(prompt))
