"""
步骤 4：网页界面。

运行：
    streamlit run app.py
"""

import streamlit as st

from answer import build_collection, search, build_prompt, make_label
from llm import call_llm

MAX_QUESTIONS = 5




# TODO 1：打开数据库 + 加载模型，只做一次
@st.cache_resource
def load_resources():
    collection = build_collection()
    return collection


# TODO 7：检索 → 拼 prompt → 调模型，结果按"问题"缓存
@st.cache_data(ttl="7d", max_entries=500, show_spinner=False)
def answer_question(question: str):
    print(f"[LLM] 缓存未命中，调用模型：{question!r}")
    collection = load_resources()
    results = search(collection, question, k=8)
    prompt = build_prompt(question, results)
    answer = call_llm(prompt)
    return answer, results


# TODO 2：页面标题和一句说明
st.title("劳动权益问答助手")
st.caption("收录《劳动法》《劳动合同法》《职工带薪年休假条例》。输入问题，系统会检索相关条款并给出回答。")

# TODO 8：每个访客的计数，第一次打开页面时初始化
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "last_question" not in st.session_state:
    st.session_state.last_question = None

# TODO 3：输入框
ask_question = st.text_input("请输入您的问题：", placeholder="例如：怎么请年假？")
count_box = st.empty()

if ask_question:
    is_new = ask_question != st.session_state.last_question
    if is_new:
        if st.session_state.question_count >= MAX_QUESTIONS:
            st.warning(f"每位访客最多可以提问 {MAX_QUESTIONS} 次，您的次数已用完。")
            st.stop()
        st.session_state.question_count += 1
        st.session_state.last_question = ask_question
    count_box.caption(f"已提问 {st.session_state.question_count} / {MAX_QUESTIONS} 次")

    # TODO 4：等待提示
    try:
        with st.spinner("正在检索相关条款并生成回答，请稍候..."):
            answer, results = answer_question(ask_question)
    except Exception as e:
        if is_new:
            st.session_state.question_count -= 1
            st.session_state.last_question = None
        print(f"[call_llm 失败] {type(e).__name__}: {e}")
        st.error(f"生成回答时出错，请稍后再试。")
        st.stop()

    # TODO 5：显示回答
    st.write(answer)

    # TODO 6：条款原文
    with st.expander("点击展开查看条款原文", expanded=False):
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            label = make_label(meta)
            st.write(f"{label}:")
            st.write(meta.get("article_text"))
