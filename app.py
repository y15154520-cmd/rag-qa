"""
步骤 4：网页界面。

运行：
    streamlit run app.py

页面：
    - 标题 + 一句说明（这是什么、能问什么）
    - 一个输入框
    - 回答正文
    - 依据（单独显示，跟正文分开）
"""

import streamlit as st

from answer import build_collection, search, build_prompt, make_label
from llm import call_llm


# TODO 1：打开数据库 + 加载模型，只做一次
#   要回答的问题：用户每回车一次，整个脚本从头跑一遍 —— 怎么让模型只加载一次？
@st.cache_resource
def load_resources():
    collection = build_collection()
    return collection

# TODO 2：页面标题和一句说明
st.title("劳动权益问答助手")
st.caption("收录《劳动法》《劳动合同法》《职工带薪年休假条例》。输入问题，系统会检索相关条款并给出回答。")

# TODO 3：输入框；用户输入了问题才往下走
ask_question = st.text_input("请输入您的问题：", placeholder="例如：怎么请年假？")

# TODO 4：检索 → 拼 prompt → 调模型（等待时给用户一点提示，别让页面看起来像卡死了）
if ask_question:
    with st.spinner("正在检索相关条款并生成回答，请稍候..."):

        collection = load_resources()
        results = search(collection, ask_question, k=8)
        prompt = build_prompt(ask_question, results)
        answer = call_llm(prompt)
# TODO 5：显示回答（第一版：整段打印就行）
    st.write(answer)

# TODO 6（做完前面再做）：在回答下面，让用户能展开看到检索到的条款原文
#   原文从哪里拿？—— 检索结果 results 里本来就有条号、章节、原文，不用从模型的回答里拆
    with st.expander("点击展开查看条款原文", expanded=False):
        for i in range(len(results['ids'][0])):
            article = results['ids'][0][i]
            meta = results['metadatas'][0][i]
            label = make_label(meta)
            st.write(f"{label}:")
            st.write(f"{results['documents'][0][i]}")
