"""
提交前检查：每次 git commit 之前运行一次。

    python precommit_check.py

检查项：
    1. .env 被 .gitignore 挡住了（没挡住 → 报警并停止）
    2. 列出将要提交的改动，提交前看一眼
"""

import subprocess
import sys


def check_env_ignored():
    """
    运行 git check-ignore -q .env，根据退出码判断 .env 是否被挡住。

    要回答的问题：
      - 退出码是多少时，说明 .env 没被挡住？
      - 没挡住时，打印什么提示？脚本还要不要继续往下走？
    """
    reults = subprocess.run(["git", "check-ignore", "-q", ".env"])
    if reults.returncode == 0:
        print(".env is ignored by .gitignore.")
    else:
        print(".env is NOT ignored by .gitignore. Please add it to .gitignore before committing.")
        sys.exit(1)


def show_changes():
    """运行 git status --short，把结果打印出来。"""
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    print("Working tree changes:")
    print(result.stdout)


if __name__ == "__main__":
    check_env_ignored()
    show_changes()

    # 验收：怎么证明这个脚本真的会报警？（写完以后亲手让它失败一次）
