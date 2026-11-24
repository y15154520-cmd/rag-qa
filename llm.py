"""
调用大模型的适配层：主流程只调用 call_llm(prompt)，不需要知道背后是哪一家。

当前实现：DeepSeek（OpenAI 兼容接口），Key 从环境变量 DEEPSEEK_API_KEY 读取
（本地放在 .env 里；部署时放在平台的密文变量里）。
"""

import os

from dotenv import load_dotenv
from openai import OpenAI


def call_llm(prompt, model="deepseek-flash", max_tokens=5000):
    """
    发送 prompt，返回模型的回答文字。

    max_tokens 设为 5000：模型回答前会先"思考"，思考用的 token 也计入上限；
    上限只是封顶，按实际用量计费，调高不会多花钱。
    出错一律抛异常（不返回错误文字），这样上层的缓存不会把错误当成结果存下来。
    """
    load_dotenv()  # 没有 .env 文件时什么也不做，Key 直接从环境变量读
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise ValueError("DEEPSEEK_API_KEY not found in environment variables. Please add it to your .env file.")
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    text = response.choices[0].message.content or ""
    reason = response.choices[0].finish_reason
    if reason == "length":
        raise ValueError("The model stopped because it reached the max token limit. Consider increasing max_tokens.")
    if text.strip() == "":
        raise ValueError("The model returned an empty response. Please check the prompt or try again.")

    return text


if __name__ == "__main__":
    # 冒烟测试：确认 Key 和网络都通
    print(call_llm("用一句话介绍你自己。"))
