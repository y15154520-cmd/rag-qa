"""
提交前检查：每次 git commit 之前运行一次。

    python precommit_check.py

检查项：
    1. .env 被 .gitignore 挡住了（没挡住 → 报警并以退出码 1 结束）
    2. 列出将要提交的改动，提交前看一眼
"""

import subprocess
import sys


def check_env_ignored():
    """git check-ignore -q .env：退出码 0 表示被忽略，否则说明 .env 会被提交。"""
    result = subprocess.run(["git", "check-ignore", "-q", ".env"])
    if result.returncode == 0:
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
