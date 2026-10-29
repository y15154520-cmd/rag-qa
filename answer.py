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

def search(collection, question, k=5):
    """问一个问题，返回最相近的 k 块。"""
    results = collection.query(
        query_texts=[question],
        n_results=k
    )
    return results

def build_prompt(question, results):
    prompt = f"请根据以下资料回答问题：\n\n"
    for i in range(len(results['documents'][0])):
        chapter = results['metadatas'][0][i].get('chapter')
        article = results['ids'][0][i]
        content = results['documents'][0][i]
        prompt += f"【{chapter} {article}】{content}\n\n"
    prompt += f"问题：{question}\n\n"
    prompt += "用自然、口语化的一段话回答，像在跟同事解释一样，不要使用“依据”“结论”这类小标题并且在同一语境下不要重复说一些内容，能让人听明白是什么即可。请只根据以上资料回答问题，不要使用你自己的知识，如果资料能完整回答，则先写依据，再写结论；如果资料只能回答一部分，则写出能回答的部分和依据，再明确说出资料里没有的是哪一部分；如果在检索到的条款中没有找到相关规定，则请直接回答“在检索到的条款中没有找到相关规定”，不要猜测，不要补充。回答的最后另起一行，写：依据：《劳动法》第X章，X条，比如“依据：《劳动法》第四章 第四十五条”。回答里提到资料时，用“我查到的《劳动法》相关条款”这类说法，不要出现“资料”两个字。资料么覆盖的部分，个固定建议一句“建议咨询单位人事部门”。"
    return prompt


if __name__ == "__main__":
    collection = build_collection()
    while True:
        question = input("请输入问题（输入 exit 或 quit 退出）：")
        if question ==  '':
            continue
        if question.lower() in ['exit', 'quit']:
            break
        results = search(collection, question)
        prompt = build_prompt(question, results)
        print(call_llm(prompt))

