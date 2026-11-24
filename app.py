"""
Streamlit 网页：输入问题 → 检索相关条款 → 大模型作答，可展开查看条款原文。

运行：
    streamlit run app.py

防刷：每个访客最多提问 MAX_QUESTIONS 次；一字不差的问题走缓存，不再调用模型。
"""

import streamlit as st

from answer import build_collection, search, build_prompt, make_label
from llm import call_llm

MAX_QUESTIONS = 5


@st.cache_resource
def load_resources():
    """打开向量库（同时加载 embedding 模型），整个进程只做一次。"""
    collection = build_collection()
    return collection


@st.cache_data(ttl="7d", max_entries=500, show_spinner=False)
def answer_question(question: str):
    """检索 → 拼 prompt → 调模型。结果按问题缓存，所有访客共用；抛出的异常不会被缓存。"""
    print(f"[LLM] 缓存未命中，调用模型：{question!r}")
    collection = load_resources()
    results = search(collection, question, k=8)
    prompt = build_prompt(question, results)
    answer = call_llm(prompt)
    return answer, results


st.title("劳动权益问答助手")
st.caption("收录《劳动法》《劳动合同法》《职工带薪年休假条例》。输入问题，系统会检索相关条款并给出回答。")

# 每个访客的提问次数（存在 session_state 里，刷新页面会清零）
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "last_question" not in st.session_state:
    st.session_state.last_question = None

ask_question = st.text_input("请输入您的问题：", placeholder="例如：怎么请年假？")
count_box = st.empty()  # 先占位，等次数加完再显示

if ask_question:
    # Streamlit 每次交互都会重跑整个脚本，输入框里的字还在；只有新问题才计次
    is_new = ask_question != st.session_state.last_question
    if is_new:
        if st.session_state.question_count >= MAX_QUESTIONS:
            st.warning(f"每位访客最多可以提问 {MAX_QUESTIONS} 次，您的次数已用完。")
            st.stop()
        st.session_state.question_count += 1
        st.session_state.last_question = ask_question
    count_box.caption(f"已提问 {st.session_state.question_count} / {MAX_QUESTIONS} 次")

    try:
        with st.spinner("正在检索相关条款并生成回答，请稍候..."):
            answer, results = answer_question(ask_question)
    except Exception as e:
        # 用户什么都没拿到，退回这次计数
        if is_new:
            st.session_state.question_count -= 1
            st.session_state.last_question = None
        print(f"[call_llm 失败] {type(e).__name__}: {e}")  # 写进日志，排查用
        st.error("生成回答时出错，请稍后再试。")
        st.stop()

    st.write(answer)

    # 条款原文直接取自检索结果，不从模型的回答里解析
    with st.expander("点击展开查看条款原文", expanded=False):
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            label = make_label(meta)
            st.write(f"{label}:")
            st.write(meta.get("article_text"))
