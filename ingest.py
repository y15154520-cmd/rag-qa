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
# 项号：全角"（一）"或半角"(一)"都认；只认紧跟在 ：；。 后面的，
# 避免把正文里引用的"第（一）项"误当成项号
ITEM_RE = re.compile(r"(?<=[：；。:;])[（(][一二三四五六七八九十]+[)）]")


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


def split_into_items(chunk):
    """
    TODO（② 拆项）：把一条"有下列情形之一的……（一）……（二）……"拆成一项一块。

    输入：split_into_articles 切出来的一块（一整条），例如劳动合同法第四十六条
    返回：一个列表，每个元素是一个"小块"字典

    例（第四十六条拆出来的第 3 块）：
        {"law": "劳动合同法", "chapter": ..., "section": ..., "article": "第四十六条",
         "item": 3,
         "text": "有下列情形之一的，用人单位应当向劳动者支付经济补偿：（三）用人单位依照本法第四十条规定解除劳动合同的；",
         "article_text": "（第四十六条整条原文）"}

    每个小块都带 article_text = 拆之前的整条原文。只有这里还拿得到整条，
    拆完以后 text 就只剩一项了，下游（build_index）再想要整条已经来不及。

    要回答的问题（先口述再写）：
      1. 怎么知道一条"有项"？没有项的条（比如第十条），返回什么？
      2. 总起那句话在哪里结束？（看原文：它后面紧跟着什么符号？）
      3. 用什么把 "（一）……（二）……" 切开？切完以后"（一）"这几个字还在不在？
      4. 第三十八条在最后一项后面还有一段"用人单位以暴力、威胁……"，这一段怎么办？
      5. ⚠️ 去看一眼《年休假条例》第四条的原文：它的"(一)"，括号和劳动合同法的一样吗？
         （你已经在页码上吃过一次全角/半角的亏了）

    验收（写在文件末尾的验收区）：
      - 劳动合同法第四十六条 → 拆成几块？第 3 块的 text 是不是上面那个样子？
      - 劳动合同法第三十八条 → 最后那段"用人单位以暴力……"有没有丢？
      - 劳动合同法第十条（没有项）→ 原样返回 1 块
      - 条例第四条 → 能拆开吗？
      - 所有小块的 text 拼起来，有没有丢字？（想想怎么检查）
    """
    text = chunk["text"]
    base = {**chunk, "article_text": text}     # 拆之前先记下整条原文
    marks = list(ITEM_RE.finditer(text))

    if not marks:
        return [{**base, "item": None}]

    groups = [[marks[0]]]
    for m in marks[1:]:
        if m.group()[1:-1] == "一":
            groups.append([m])
        else:
            groups[-1].append(m)

    pieces = []
    n = 0
    lead_start = 0
    for gi, group in enumerate(groups):
        lead = text[lead_start:group[0].start()]
        group_end = groups[gi + 1][0].start() if gi + 1 < len(groups) else len(text)

        bodies = []
        for i, m in enumerate(group):
            end = group[i + 1].start() if i + 1 < len(group) else group_end
            bodies.append(text[m.start():end])

        rest = ""
        cut = bodies[-1].find("。")
        if cut != -1:
            bodies[-1], rest = bodies[-1][:cut + 1], bodies[-1][cut + 1:]
        lead_start = group_end - len(rest)

        for body in bodies:
            n += 1
            pieces.append({**base, "item": n, "text": lead + body})

    tail = text[lead_start:]
    if tail:
        pieces.append({**base, "item": None, "text": tail})
    return pieces


def rebuild_text(pieces):
    """从小块还原整条原文：总起句只算一次，用来检查有没有丢字。"""
    out, prev_lead = [], None
    for p in pieces:
        if p["item"] is None:
            out.append(p["text"])
            continue
        m = ITEM_RE.search(p["text"])
        lead = p["text"][:m.start()]
        if lead != prev_lead:          
            out.append(lead)
            prev_lead = lead
        out.append(p["text"][m.start():])
    return "".join(out)


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

    # ---------------- ② 拆项验收 ----------------
    print("\n拆项：")
    contract = [c for c in all_chunks if c["law"] == "劳动合同法"]

    p46 = split_into_items(find_article(contract, "第四十六条"))
    check("劳动合同法第四十六条 块数", 7, len(p46))
    check("第四十六条 第 3 块",
          "有下列情形之一的，用人单位应当向劳动者支付经济补偿：（三）用人单位依照本法第四十条规定解除劳动合同的；",
          p46[2]["text"])
    check("第四十六条 第 3 块 item", 3, p46[2]["item"])

    p38 = split_into_items(find_article(contract, "第三十八条"))
    check("第三十八条 尾段'用人单位以暴力'没丢", True,
          any(p["text"].startswith("用人单位以暴力") for p in p38))
    check("第三十八条 第 6 项不含尾段", False, "暴力" in p38[5]["text"])

    p10 = split_into_items(find_article(contract, "第十条"))
    check("劳动合同法第十条 块数", 1, len(p10))
    check("第十条 text 原样", find_article(contract, "第十条")["text"], p10[0]["text"])

    p41 = split_into_items(find_article(contract, "第四十一条"))
    check("劳动合同法第四十一条 块数（4 项 + 3 项 + 尾段）", 8, len(p41))
    check("第四十一条 第 5 块（第二组第一项）",
          "裁减人员时，应当优先留用下列人员：（一）与本单位订立较长期限的固定期限劳动合同的；",
          p41[4]["text"])
    check("第四十一条 第 4 块不带下一组的总起句", False, "优先留用" in p41[3]["text"])

    p4 = split_into_items(find_article(regs, "第四条"))
    check("条例第四条 块数", 5, len(p4))

    # 丢字检查：每一条拆完再拼回去，必须和原文一字不差；项号必须从 1 连续编号
    lost, bad_seq = [], []
    for c in all_chunks:
        pieces = split_into_items(c)
        if rebuild_text(pieces) != c["text"]:
            lost.append(f"{c['law']}{c['article']}")
        nums = [p["item"] for p in pieces if p["item"] is not None]
        if nums != list(range(1, len(nums) + 1)):
            bad_seq.append(f"{c['law']}{c['article']}")
    check("拼回去和原文不一致的条", [], lost)
    check("项号不连续的条", [], bad_seq)
    check("article_text 不是整条原文的小块数", 0,
          sum(1 for c in all_chunks for p in split_into_items(c) if p["article_text"] != c["text"]))
    all_pieces = [p for c in all_chunks for p in split_into_items(c)]
    print(f"  拆项后共 {len(all_pieces)} 块（拆项前 {len(all_chunks)} 块）")
