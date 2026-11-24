"""
把检索包成 MCP 工具，让 Claude Code 这类支持 MCP 的 AI 应用自己调用"查劳动法"。

安装（已包含在 requirements.txt）：
    pip install "mcp[cli]<2"

运行：
    python mcp_server.py
    → 在 http://localhost:8000/mcp 提供服务

接进 Claude Code（服务要保持运行）：
    claude mcp add --transport http labor-law http://localhost:8000/mcp

工具只做检索，不调用大模型：调用方本身就是大模型，会自己读条款写回答。
"""

from mcp.server.fastmcp import FastMCP

from answer import build_collection, search, make_label

mcp = FastMCP("劳动法检索工具")

# 写在最外层：启动时加载一次向量库和 embedding 模型，之后每次调用只做检索
collection = build_collection()


@mcp.tool()
def search_labor_law(question: str) -> str:
    """检索中国劳动法规条文，返回最相关的若干条法条原文（带法律名、章、节、条号）。

    能查的范围（只有这三部）：
      - 《中华人民共和国劳动法》
      - 《中华人民共和国劳动合同法》
      - 《职工带薪年休假条例》

    什么时候用：用户问劳动关系相关的问题时，例如劳动合同的订立/解除/续签、
    试用期、工资和拖欠工资、加班和工作时间、休息休假、年休假、经济补偿、
    女职工保护等。回答前先调用本工具，并在回答中引用返回的条款。

    参数：
      question：用户的问题，中文大白话即可，例如"公司拖欠工资怎么办？"。
                一次只问一个问题；如果用户问了几件事，分开多次调用。

    查不到的：工伤认定和工伤保险待遇（《工伤保险条例》）、社会保险缴费细则
    （《社会保险法》）、各地方性法规和最低工资标准、司法解释和具体判例都不在库里。
    遇到这些问题，告诉用户本工具查不到，不要把检索到的不相关条款当成依据。
    """
    results = search(collection, question, k=8)
    metas = results["metadatas"][0]
    if not metas:
        return "没有检索到相关条款。"

    blocks = []
    for i, meta in enumerate(metas, start=1):
        label = make_label(meta)
        # article_text 每块都有；缺了说明建库出错，宁可报错也不悄悄返回半条
        blocks.append(f"[{i}] {label}\n{meta['article_text']}")
    return "\n\n".join(blocks)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
