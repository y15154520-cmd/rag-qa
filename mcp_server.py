"""
④ 把检索包成 MCP 工具：让 Claude 这类 AI 应用自己调用"查劳动法"。

安装（只装一次，在 .venv 里）：
    pip install "mcp[cli]<2"

运行：
    python mcp_server.py
    → 启动后是本机上的一个小服务，地址 http://localhost:8000/mcp

接进 Claude Code（另开一个终端，服务要一直开着）：
    claude mcp add --transport http labor-law http://localhost:8000/mcp

官方文档：https://github.com/modelcontextprotocol/python-sdk （看 v1.x 分支的 README）
"""

# TODO 1：import
#   要用到的：官方 SDK 里的 FastMCP（import 那一行去 README 的 Quickstart 里找，别凭感觉写）
#             answer.py 里现成的 build_collection / search / make_label
#   要回答的问题：answer.py 里有没有会往终端 print 的东西？这次用 http 方式启动，print 不会坏事；
#                但如果以后换成 stdio 方式，print 到标准输出会把协议搞乱 —— 先记住这件事
from mcp.server.fastmcp import FastMCP

from answer import build_collection, search, make_label

# TODO 2：建服务对象
#   要回答的问题：FastMCP("名字") 里的名字是给谁看的？起一个别人一眼能看懂的名字

mcp = FastMCP("劳动法检索工具")
# TODO 3：打开数据库 + 加载 embedding 模型
#   要回答的问题：网页里你用 @st.cache_resource 保证只加载一次。
#                这里没有 Streamlit 了，怎么保证不是"每调用一次工具就加载一次模型"？
#                提示：想想这个文件被运行的时候，最外层（不在任何函数里）的代码执行几次
collection = build_collection()


# TODO 4：工具函数 search_labor_law
#   输入：question（用户的问题，大白话就行）
#   输出：检索到的条款，每条要带标签（哪部法、第几章、第几条）和整条原文
#   要回答的问题（先口述再写）：
#     1. 上面加什么装饰器，它才会变成 MCP 工具？
#     2. 参数和返回值要不要写类型标注（如 question: str）？官方例子写了 —— 想想 Claude 怎么知道参数该填什么类型
#     3. docstring 写四件事：能查什么（三部法写全名）、什么时候该用、参数怎么填、不能查什么
#     4. 返回一整段拼好的文字（str），还是一个列表、每条一个字典？各有什么好处？先用你觉得简单的那种
#     5. k 取几？网页里是 8 —— 这里要不要一样？
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
        blocks.append(f"[{i}] {label}\n{meta['article_text']}")
    return "\n\n".join(blocks)


# TODO 5：启动
#   要回答的问题：为什么要放在 if __name__ == "__main__": 下面？（你 11-10 在这里栽过一次）
#   启动方式照 README：transport="streamable-http"
if __name__ == "__main__":
    mcp.run(transport="streamable-http")


# 验收（写完以后做）：
#   1. python mcp_server.py 能启动，终端没报错
#   2. 接进 Claude Code，在一个新的 Claude Code 会话里问"公司拖欠工资怎么办？"，
#      看它有没有调用 search_labor_law、回答里有没有引用条款
#   3. 问一个工伤的问题，看它是不是知道这个工具查不到
