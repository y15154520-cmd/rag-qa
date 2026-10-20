"""
步骤 1：读取《劳动法》PDF，清洗，按"条"切块。

输出：一个列表，每个元素是一块（一个字典）：
    {"chapter": "第四章 工作时间和休息休假", "article": "第四十五条", "text": "国家实行带薪年休假制度。……"}

验收标准（《劳动法》共 107 条）：
    - 块数 == 107
    - 第一块的 article 是 "第一条"，最后一块是 "第一百零七条"
    - 第四十五条（带薪年休假）的 chapter 是 "第四章 工作时间和休息休假"
"""

from pathlib import Path
from pypdf import PdfReader
import re
PDF_PATH = Path(__file__).parent / "data" / "labor_law.pdf"


def load_pdf_text(path):
    """读出 PDF 每一页的文字，拼成一整篇，返回字符串。"""
    text = ""
    pdf = PdfReader(path)
    for page in pdf.pages:
        text += page.extract_text() + "\n"
    return text

def clean_text(text):
    """删掉页码（形如 －11－）。返回清洗后的字符串。"""
    before_len = len(re.findall(r"－\d+－", text))  # 统计页码数量
    cleaned_text = re.sub(r"－\d+－", "", text)
    after_len = len(re.findall(r"－\d+－", cleaned_text))
    print(f"删前页码数量：{before_len}，删后页码数量：{after_len}")
    return cleaned_text

def split_into_articles(text):
    """
    一行一行往下读，切成"条"，返回块的列表。

    要回答的问题（先想清楚再写）：
      1. 怎么判断一行是"章节标题"？怎么判断一行是"一条的开头"？其余的行是什么？
      2. 读到第四十六条时，它怎么知道自己属于第五章？（要在循环外面记住什么？）
      3. 一条的内容跨了好几行，这几行怎么接到同一块上？
      4. 第一章出现之前，PDF 开头还有标题、修正说明等内容，它们该去哪？
      5. 循环结束时，手上还拿着的最后一条，进列表了吗？
    """
    # TODO
    pass


if __name__ == "__main__":
    text = clean_text(load_pdf_text(PDF_PATH))
    chunks = split_into_articles(text)
    print(text[:200])
    # TODO：对照文件开头的验收标准，把每一条都检查一遍并打印结果
