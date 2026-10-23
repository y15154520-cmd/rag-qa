"""
步骤 2：把切好的 107 块存进 Chroma，并做一次检索实验。

实验 A（本文件第一版）：用 Chroma 默认的 embedding 模型（all-MiniLM-L6-v2，英文训练）
    问 "怎么请年假？"，看第四十五条（带薪年休假）排第几。
    → 这是对照组。之后换中文模型再跑一次，两次结果放在一起比。

验收：
    - collection 里正好 107 条
    - 打印出前 3 名的 article / chapter / distance
    - 重复运行两次，collection 里仍然是 107 条
"""

from pathlib import Path
from chromadb.errors import NotFoundError
import chromadb

from ingest import PDF_PATH, load_pdf_text, clean_text, split_into_articles

DB_PATH = Path(__file__).parent / "chroma_db"    # 已在 .gitignore 里
COLLECTION_NAME = "labor_law"


def build_collection(chunks):
    """
    把块存进 Chroma，返回 collection。

    要回答的问题（先想清楚再写）：
      1. 距离度量用什么？Chroma 的默认值是什么？
      2. add() 要三个列表：ids / documents / metadatas，第 i 个位置对应第 i 块。
         每一块的这三样分别是什么？
      3. id 用什么？要求：每块唯一；重复运行时，同一条法律的 id 不变。
      4. 运行第二次时会发生什么？collection 里会变成 214 条吗？
    """
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except NotFoundError:
        pass
    collection = client.create_collection(
        name = COLLECTION_NAME,
        configuration = {"hnsw": {"space": "cosine"}}
    )

    ids = []
    documents = []
    metadatas = []
    for chunk in chunks:
        ids.append(chunk["article"])
        documents.append(chunk["text"])
        metadatas.append({"chapter": chunk["chapter"]})
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return collection

def search(collection, question, k=3):
    """问一个问题，返回最相近的 k 块。"""
    results = collection.query(
        query_texts=[question],
        n_results=k
    )
    return results


if __name__ == "__main__":
    chunks = split_into_articles(clean_text(load_pdf_text(PDF_PATH)))
    collection = build_collection(chunks)

    # TODO：打印 collection 里的条数
    print(collection.count())
    # TODO：问 "怎么请年假？"，打印前 3 名的 article / chapter / distance
    question = "怎么请年假？"
    results = search(collection, question, k=3)
    for i, (article, chapter, distance) in enumerate(zip(results["ids"][0], results["metadatas"][0], results["distances"][0])):
        print(f"第 {i+1} 名: article={article}, chapter={chapter}, distance={distance}")

