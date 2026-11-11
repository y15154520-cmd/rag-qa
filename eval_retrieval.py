"""
检索评测：对一组问题，检查"应该找到的条款"有没有出现在前 k 名里。

只测检索，不调模型 —— 不花钱、跑得快。

运行：
    python eval_retrieval.py
"""

from answer import build_collection, search

# 标准答案：每个问题，应该被找到的条款（对照三部法原文逐条核对过；只收"直接回答了这个问题"的条款）
TEST_CASES = [
    # 劳动法第四十五条：国家实行带薪年休假制度
    # 条例第二条：连续工作 1 年以上享受年休假；条例第五条：单位统筹安排、考虑本人意愿、可集中可分段
    # （条例第三条讲"几天"，不是"怎么请"，不算）
    {"question": "怎么请年假？",
     "expected": ["劳动法_第四十五条", "职工带薪年休假条例_第二条", "职工带薪年休假条例_第五条"]},
    # 劳动法第七十九条：调解 → 仲裁 → 诉讼的流程；第八十二条：六十日内提出书面申请
    # （劳动合同法第七十七条只说"有权申请仲裁"，没讲怎么申请、多久，不算）
    {"question": "怎么申请劳动仲裁？有时间限制吗？",
     "expected": ["劳动法_第七十九条", "劳动法_第八十二条"]},
    # 劳动法第三十六条：每日不超过八小时；第四十一条：延长每日一般不超过一小时、特殊不超过三小时
    # 劳动合同法第三十一条：不得强迫或者变相强迫劳动者加班
    {"question": "公司能不能让我每天工作12小时？",
     "expected": ["劳动法_第三十六条", "劳动法_第四十一条", "劳动合同法_第三十一条"]},
    # 劳动法第二十一条：最长不得超过六个月
    # 劳动合同法第十九条：按合同期限分档，一个月 / 二个月 / 六个月
    {"question": "试用期最长可以多久？",
     "expected": ["劳动法_第二十一条", "劳动合同法_第十九条"]},
    # 劳动法第四十四条：加班 150% / 休息日 200% / 法定休假日 300%
    # （劳动合同法第三十一条只说"按国家有关规定支付"，没讲怎么算，不算）
    {"question": "加班费怎么算？",
     "expected": ["劳动法_第四十四条"]},

    # ---------- ② 扩大评测集（2026-11-11 新增 13 题，标准同上） ----------
    # 劳动合同法第十条：未同时订立的，自用工之日起一个月内订立
    # （劳动法第十六条只说"应当订立"，没说多久，不算）
    {"question": "入职多久公司必须跟我签劳动合同？",
     "expected": ["劳动合同法_第十条"]},
    # 劳动合同法第八十二条：超过一个月不满一年未签 → 每月二倍工资
    {"question": "公司一直不跟我签合同，我能要求什么赔偿？",
     "expected": ["劳动合同法_第八十二条"]},
    # 劳动合同法第四十六条：应当支付经济补偿的情形；劳动法第二十八条：依法解除的应当给予经济补偿
    {"question": "被公司辞退有没有经济补偿？",
     "expected": ["劳动合同法_第四十六条", "劳动法_第二十八条"]},
    # 劳动合同法第四十七条：每满一年支付一个月工资，六个月以上按一年、不满六个月半个月
    {"question": "离职经济补偿怎么算？",
     "expected": ["劳动合同法_第四十七条"]},
    # 劳动合同法第三十七条：提前三十日书面通知，试用期提前三日；劳动法第三十一条：提前三十日书面通知
    {"question": "我想辞职，要提前多久通知公司？",
     "expected": ["劳动合同法_第三十七条", "劳动法_第三十一条"]},
    # 劳动合同法第二十条：不得低于相同岗位最低档或约定工资的百分之八十，且不低于当地最低工资
    {"question": "试用期工资最低能给多少？",
     "expected": ["劳动合同法_第二十条"]},
    # 劳动合同法第三十条：可向法院申请支付令；第三十八条：可以解除劳动合同
    # 劳动合同法第八十五条、劳动法第九十一条：劳动行政部门责令支付
    # （劳动法第五十条只说"不得拖欠"，没说拖欠了怎么办，不算）
    {"question": "公司拖欠工资怎么办？",
     "expected": ["劳动合同法_第三十条", "劳动合同法_第三十八条", "劳动合同法_第八十五条", "劳动法_第九十一条"]},
    # 劳动合同法第四十二条、劳动法第二十九条：孕期、产期、哺乳期不得依相关条款解除
    {"question": "怀孕期间公司能辞退我吗？",
     "expected": ["劳动合同法_第四十二条", "劳动法_第二十九条"]},
    # 劳动合同法第八十七条：按经济补偿标准的二倍支付赔偿金；第四十八条：可要求继续履行或依第八十七条赔偿
    {"question": "公司违法辞退我，要赔多少钱？",
     "expected": ["劳动合同法_第八十七条", "劳动合同法_第四十八条"]},
    # 劳动合同法第六十三条：被派遣劳动者享有同工同酬的权利
    {"question": "劳务派遣工和正式员工工资一样吗？",
     "expected": ["劳动合同法_第六十三条"]},
    # 劳动合同法第二十四条：竞业限制期限不得超过二年
    # （第二十三条讲可以约定竞业限制和经济补偿，没讲多久，不算）
    {"question": "竞业限制最长多久？",
     "expected": ["劳动合同法_第二十四条"]},
    # 条例第五条：应休未休的，按日工资收入的 300% 支付
    # （条例第七条讲单位不给时由谁责令、加付赔偿金，是"不给怎么办"，不算）
    {"question": "年假没休完，公司要怎么补偿？",
     "expected": ["职工带薪年休假条例_第五条"]},
    # 劳动法第四十八条：最低工资具体标准由省级政府规定，不得低于当地最低工资标准
    {"question": "最低工资是多少？",
     "expected": ["劳动法_第四十八条"]},
]


def evaluate(collection, k):
    """
    对每个问题检索前 k 条，打印一行结果：问题 / 应该找到的 / 实际找到了哪几条 / 漏了哪几条。

    要回答的问题：
      1. "找到了"怎么判断？（提示：expected 里的条号，在不在前 k 名的 ids 里）
      2. expected 是空列表的问题，这一行该怎么判断？
      3. 最后算一个总分：所有问题加起来，应该找到的条款一共几条，实际找到了几条？
    """
    total_expected = 0
    total_found = 0
    missed = []
    for test_case in TEST_CASES:
        question = test_case["question"]
        expected = test_case["expected"]
        results = search(collection, question, k)
        found = results['ids'][0]
        missed.append([e for e in expected if e not in found])
        total_expected += len(expected)
        total_found += len([e for e in expected if e in found])
    return total_expected, total_found, missed


def find_ranks(collection, question, expected, max_k=30):
    """
    TODO（② 扩大评测集）：每条标准答案，排在第几名？

    输入：
        question  一个问题，如 "加班费怎么算？"
        expected  这题的标准答案列表，如 ["劳动法_第四十四条"]
        max_k     最多看到第几名（超过就算"没找到"）
    返回：
        一个字典，标准答案 → 名次（从 1 开始数）；前 max_k 名里没有的 → None
        例：{"劳动法_第四十四条": 6}

    要回答的问题（先口述再写）：
      1. 要检索几条？k 是多少？
      2. 拿到 results['ids'][0] 这个列表以后，怎么知道某个 id 排在第几？
         —— 先用笨办法：自己写循环数。写出来以后再看有没有现成的方法
      3. 名次从 1 开始还是从 0 开始？列表下标从几开始？
      4. 不在列表里的那条，怎么判断、怎么处理？会不会报错？
    """
    results = search(collection, question, max_k)
    found = results['ids'][0]
    ranks = {}
    for e in expected:
        if e in found:
            ranks[e] = found.index(e) + 1  # 名次从 1 开始
        else:
            ranks[e] = None  # 没找到
    return ranks


if __name__ == "__main__":
    collection = build_collection()
    for k in range(1,9):
        print(f"===== k = {k} =====")
        total_expected, total_found, missed = evaluate(collection, k)
        print(f"总分：{total_found} /{total_expected} ")
        print(f"漏掉的条款：{missed}")

    # TODO（② 扩大评测集）：逐题打印每条标准答案的名次
    #   期望输出长这样（数字是举例）：
    #       加班费怎么算？
    #           劳动法_第四十四条  第 6 名
    #       怎么请年假？
    #           劳动法_第四十五条  第 8 名
    #           职工带薪年休假条例_第二条  第 7 名
    #           ……
    #   没找到的打印"30 名以外"
    for test_case in TEST_CASES:
        question = test_case["question"]
        expected = test_case["expected"]
        ranks = find_ranks(collection, question, expected, max_k=30)
        print(f"问题：{question}")
        for e in expected:
            rank = ranks[e]
            if rank is not None:
                print(f"    {e}  第 {rank} 名")
            else:
                print(f"    {e}  排名以外")
