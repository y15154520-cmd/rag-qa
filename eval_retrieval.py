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


if __name__ == "__main__":
    collection = build_collection()
    for k in range(1,9):
        print(f"===== k = {k} =====")
        total_expected, total_found, missed = evaluate(collection, k)
        print(f"总分：{total_found} /{total_expected} ")
        print(f"漏掉的条款：{missed}")
