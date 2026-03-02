"""
python -m synapse で実行可能にする
"""
from synapse.engine import run_synapse_with_callback

if __name__ == "__main__":
    goal = input("何を作りますか？ > ")
    if not goal.strip():
        goal = "電卓アプリをPythonで作ってください。四則演算ができるCUIアプリ。"
    result = run_synapse_with_callback(goal)
    print(f"\n承認: {result['approved']}")
    print(f"ラウンド: {result['rounds']}")
    print(f"ログ: {result['log_path']}")
