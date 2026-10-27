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


def retrieve(question, k=3):
    """
    从已经建好的 collection 里找出最相关的 k 条。

    要回答的问题：
      1. 这里应该"重建索引"还是"直接打开已有的"？为什么？
      2. 打开已有的 collection 时，为什么还要再指定一次 embedding 模型？
         （提示：问题也要变成向量才能去比。用的尺子必须和存的时候一样）
    """
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=Text2VecEmbeddingFunction())
    results = collection.query(
        query_texts=[question],
        n_results=k,
    )
    return results


def build_prompt(question, results):
    """
    把检索结果和问题拼成一个 prompt，返回字符串。

    三件事（照着 FAQ 机器人那个例子搬过来）：
      1. 每条资料前面贴标签：章节 + 条号
      2. 规则：只根据资料回答；先写依据、再写结论
      3. 没找到时的出口：原话写好
    """
    prompt = f"请根据以下资料回答问题：\n\n"
    for i in range(len(results['documents'][0])):
        chapter = results['metadatas'][0][i].get('chapter')
        article = results['ids'][0][i]
        content = results['documents'][0][i]
        prompt += f"【{chapter} {article}】{content}\n\n"
    prompt += f"问题：{question}\n\n"
    prompt += "请只根据以上资料回答问题，不要使用你自己的知识，先写依据，再写结论。如果在检索到的条款中没有找到相关规定，请直接回答“在检索到的条款中没有找到相关规定”，不要猜测，不要补充。"
    return prompt


if __name__ == "__main__":
    question = "离职以后公司要我签竞业限制，补偿该给多少？"
    results = retrieve(question)
    prompt = build_prompt(question, results)
    #print(prompt)
    print(call_llm(prompt))
