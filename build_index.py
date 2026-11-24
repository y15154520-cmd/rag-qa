"""
建立向量索引：三部法切块、拆项后（共 331 块）用中文 embedding 模型向量化，存入 Chroma。

运行（生成 chroma_db/ 文件夹）：
    python build_index.py

每次运行都删表重建，重复运行结果不变（仍是 331 块）。
最后用"怎么请年假？"做一次检索，打印前几名，作为冒烟测试。
"""

from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from chromadb.utils.embedding_functions import Text2VecEmbeddingFunction

from ingest import LAWS, load_pdf_text, clean_text, split_into_articles, split_into_items

DB_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "labor_law"


def build_collection(chunks):
    """
    把块存进 Chroma，返回 collection。

    - 距离用余弦（Chroma 默认是 L2，会偏向短文本）
    - 删表重建：add() 遇到已存在的 id 会静默跳过，upsert() 删不掉已不存在的块
    - id = 法名_条号_项号（如 劳动合同法_第四十六条_3），三部法都有"第一条"，一条又会拆成几块
    - documents 存拆好的小块（用来比相似度），metadata 里另存整条原文 article_text（交给模型和展示）
    """
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except NotFoundError:
        pass
    collection = client.create_collection(
        name = COLLECTION_NAME,
        configuration = {"hnsw": {"space": "cosine"}},
        embedding_function = Text2VecEmbeddingFunction()
    )

    ids = []
    documents = []
    metadatas = []
    for chunk in chunks:
        ids.append(chunk["law"] + "_" + chunk["article"] + "_" + str(chunk["item"]))
        documents.append(chunk["text"])
        metadatas.append({"law": chunk["law"], "chapter": chunk["chapter"], "section": chunk["section"], "article": chunk["article"],
                          "article_text": chunk["article_text"]})
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return collection


def search(collection, question, k=8):
    """冒烟测试用：返回最相近的 k 块（不按条去重；正式检索见 answer.search）。"""
    results = collection.query(
        query_texts=[question],
        n_results=k
    )
    return results


if __name__ == "__main__":
    all_chunks = []
    for law in LAWS:
        articles = split_into_articles(law["name"], clean_text(load_pdf_text(law["path"])))
        for article in articles:
            all_chunks.extend(split_into_items(article))
    collection = build_collection(all_chunks)
    print(f"collection 里条数：{collection.count()}")
    question = "怎么请年假？"
    results = search(collection, question, k=8)
    for i, (article, meta, distance) in enumerate(zip(
        results["ids"][0],
        results["metadatas"][0],
        results["distances"][0])):
        print(f"第 {i+1} 名: article={article}, chapter={meta['chapter']}, section={meta['section']}, law={meta['law']}, distance={distance:.4f}")



