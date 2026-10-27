"""
调用大模型的适配层：主流程只调用 call_llm(prompt)，不需要知道背后是哪一家。

当前实现：DeepSeek（OpenAI 兼容接口），Key 从 .env 的 DEEPSEEK_API_KEY 读取。
"""

from pathlib import Path
from dotenv import load_dotenv
import os
from openai import OpenAI
def call_llm(prompt, model="deepseek-flash", max_tokens=2000):
    load_dotenv()
    client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),  # ⚠️ 这里的 env var 名字要和你 .env 里的一致
    base_url="https://api.deepseek.com"
    )
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise ValueError("DEEPSEEK_API_KEY not found in environment variables. Please add it to your .env file.")
    response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=max_tokens,
    )
    text = response.choices[0].message.content or ""
    prompt_usage = response.usage.prompt_tokens
    completion_usage = response.usage.completion_tokens
    reason = response.choices[0].finish_reason
    if reason == "length":
        raise ValueError(f"The model stopped because it reached the max token limit. Consider increasing max_tokens. Usage: {prompt_usage} + {completion_usage}")
    if text.strip() == "":
        raise ValueError(f"The model returned an empty response. Please check the prompt or try again. Usage: {prompt_usage} + {completion_usage}")

    return text, prompt_usage, completion_usage

if __name__ == "__main__":
    text, prompt_usage, completion_usage = call_llm(prompt, max_tokens=2000)
    print(text)
