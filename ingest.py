"""
步骤 1：读取三部法的 PDF，清洗，按"条"切块。

输出：一个列表，每个元素是一块（一个字典）：
    {"law": "劳动法", "chapter": "第四章 工作时间和休息休假", "section": "",
     "article": "第四十五条", "text": "国家实行带薪年休假制度。……"}

验收标准：
    - 劳动法 107 块、劳动合同法 98 块、条例 10 块，合计 215
    - 劳动法的四条老验收照样 Pass（回归测试）
    - 条例第七条的正文里，不再有 "- 2 -"
    - 条例每一块的 chapter 都不是 None
    - 每块都有 law 字段
"""

from collections import Counter
from pathlib import Path
from pypdf import PdfReader
import re

DATA_DIR = Path(__file__).parent / "data"
LAWS = [
    {"name": "劳动法",             "path": DATA_DIR / "labor_law.pdf"},
    {"name": "劳动合同法",         "path": DATA_DIR / "labor_contract_law.pdf"},
    {"name": "职工带薪年休假条例", "path": DATA_DIR / "paid_annual_leave.pdf"},
]


PDF_PATH = LAWS[0]["path"]
PAGE_NUM_RE = re.compile(r"^[ \t]*[-－][ \t]*\d+[ \t]*[-－][ \t]*$", re.MULTILINE)

CHAPTER_RE = re.compile(r"^(第[一二三四五六七八九十]+章 .+)$")
SECTION_RE = re.compile(r"^(第[一二三四五六七八九十]+节 .+)$")  
ARTICLE_RE = re.compile(r"^(第[一二三四五六七八九十百零]+条) ")


def load_pdf_text(path):
    text = ""
    pdf = PdfReader(path)
    for page in pdf.pages:
        text += page.extract_text() + "\n"
    return text


def clean_text(text):
    before_len = len(PAGE_NUM_RE.findall(text))
    cleaned_text = PAGE_NUM_RE.sub("", text)
    after_len = len(PAGE_NUM_RE.findall(cleaned_text))
    print(f"删前页码数量：{before_len}，删后页码数量：{after_len}")
    return cleaned_text


def split_into_articles(law, text):
    chunks = []
    current_chapter = ""
    current_section = ""
    current_article = None
    current_text_lines = []

    def flush():
        nonlocal current_article, current_text_lines
        if current_article and current_text_lines:
            chunks.append({
                "law": law,
                "chapter": current_chapter,
                "section": current_section,
                "article": current_article,
                "text": "".join(current_text_lines).strip(),
            })
        current_article = None
        current_text_lines = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = CHAPTER_RE.match(line)
        if m:
            flush()
            current_chapter = m.group(1)
            current_section = ""
            continue

        m = SECTION_RE.match(line)
        if m:
            flush()
            current_section = m.group(1)
            continue

        m = ARTICLE_RE.match(line)
        if m:
            flush()
            current_article = m.group(1)
            current_text_lines.append(line[len(current_article):].strip())
            continue

        if current_article:
            current_text_lines.append(line)

    flush()
    return chunks


# ---------------- 验收 ----------------

def check(label, expected, actual):
    if actual == expected:
        print(f"  {label} Pass")
    else:
        print(f"  {label} Fail：期望 {expected!r}，实际 {actual!r}")


def find_article(chunks, article):
    for c in chunks:
        if c["article"] == article:
            return c
    return None


def report_duplicates(chunks):
    counts = Counter(c["article"] for c in chunks)
    dups = [a for a, n in counts.items() if n > 1]
    if not dups:
        return
    print(f"  ⚠ 重复条号：{dups}")
    for a in dups:
        hits = [c for c in chunks if c["article"] == a]
        for c in hits[1:]:
            print(f"    {a}（{c['chapter']} {c['section']}）：{c['text'][:60]!r}")


EXPECT = {
    "劳动法": {
        "count": 107, "last": "第一百零七条",
        "probe": ("第四十五条", "第四章 工作时间和休息休假"),
    },
    "劳动合同法": {
        "count": 98, "last": "第九十八条",
        "probe": ("第四十五条", "第四章 劳动合同的解除和终止"),
    },
    "职工带薪年休假条例": {
        "count": 10, "last": "第十条",
        "probe": ("第七条", ""),
    },
}


if __name__ == "__main__":
    all_chunks = []

    for law in LAWS:
        name, path = law["name"], law["path"]
        print(f"\n正在处理 {name}（{path.name}）...")
        text = clean_text(load_pdf_text(path))
        chunks = split_into_articles(name, text)
        all_chunks.extend(chunks)

        exp = EXPECT[name]
        check("块数", exp["count"], len(chunks))
        check("第一块", "第一条", chunks[0]["article"] if chunks else None)
        check("最后一块", exp["last"], chunks[-1]["article"] if chunks else None)

        probe_article, probe_chapter = exp["probe"]
        probe = find_article(chunks, probe_article)
        check(f"{probe_article} 的 chapter", probe_chapter, probe["chapter"] if probe else None)
        check(f"{probe_article} 的 law", name, probe["law"] if probe else None)

        if name == "劳动法":
            # 查正文：加班费那条要完整，不能只剩半句
            art44 = find_article(chunks, "第四十四条")
            check("第四十四条正文含 '百分之三百'", True,
                  ("百分之三百" in art44["text"]) if art44 else None)

        report_duplicates(chunks)

    print("\n三部法汇总：")
    check("合计块数", 215, len(all_chunks))
    check("缺 law 字段的块数", 0, sum(1 for c in all_chunks if not c.get("law")))

    regs = [c for c in all_chunks if c["law"] == "职工带薪年休假条例"]
    check("条例 chapter 为 None 的块数", 0, sum(1 for c in regs if c["chapter"] is None))
    art7 = find_article(regs, "第七条")
    check("条例第七条正文含 '- 2 -'", False, ("- 2 -" in art7["text"]) if art7 else None)
