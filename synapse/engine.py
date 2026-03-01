"""
Synapse - メインエンジン
Orchestrator → Coder → Reviewer のターンベースループ
"""

import anthropic
import json
import os
from datetime import datetime
from synapse.sandbox import Sandbox
from synapse.agents import run_agent
from synapse.tools import CODER_TOOLS, REVIEWER_TOOLS
from synapse.prompts import ORCHESTRATOR_SYSTEM, CODER_SYSTEM, REVIEWER_SYSTEM
from synapse.config import (
    ORCHESTRATOR_MODEL, CODER_MODEL, REVIEWER_MODEL, MAX_ROUNDS,
)
from dotenv import load_dotenv

load_dotenv()


def run_synapse(user_goal: str) -> Sandbox:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    sandbox = Sandbox()

    # ログ設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("logs", exist_ok=True)
    log_file = open(f"logs/{timestamp}.txt", "w", encoding="utf-8")

    def log(text):
        print(text)
        log_file.write(text + "\n")
        log_file.flush()

    log(f"{'='*60}")
    log(f"Synapse v0.3.1 - Multi-Agent System")
    log(f"Goal: {user_goal}")
    log(f"{'='*60}\n")

    try:
        # Step 1: Orchestrator が計画を立てる
        log("[Orchestrator] 計画を作成中...\n")
        orch_messages = [{
            "role": "user",
            "content": f"以下のゴールの実装計画を簡潔に作成してください:\n\n{user_goal}",
        }]
        orch_reply, _ = run_agent(
            client, ORCHESTRATOR_MODEL, ORCHESTRATOR_SYSTEM,
            orch_messages, None, sandbox, log,
        )
        log(f"[Orchestrator]\n{orch_reply}\n")

        reviewer_reply = ""

        for round_num in range(1, MAX_ROUNDS + 1):
            log(f"\n{'='*40}")
            log(f"  Round {round_num}/{MAX_ROUNDS}")
            log(f"{'='*40}\n")

            # Step 2: Coder が実装
            log("[Coder] 実装中...\n")
            if round_num == 1:
                instruction = f"以下の計画に従って実装してください。ファイル数は最小限に:\n\n{orch_reply}"
            else:
                instruction = f"以下の指摘を修正してください。修正箇所のみ対応:\n\n{reviewer_reply}"

            coder_messages = [{"role": "user", "content": instruction}]
            coder_reply, _ = run_agent(
                client, CODER_MODEL, CODER_SYSTEM,
                coder_messages, CODER_TOOLS, sandbox, log,
            )
            log(f"\n[Coder]\n{coder_reply}\n")

            # Step 3: Reviewer が検証
            log("[Reviewer] レビュー中...\n")
            files = sandbox.list_files()
            review_instruction = (
                f"以下のファイルを検証してください。主要ファイルだけ読めばOK:\n"
                f"{json.dumps(files, ensure_ascii=False)}\n\n"
                f"テストが通っていればAPPROVEDとしてください。"
            )
            reviewer_messages = [{"role": "user", "content": review_instruction}]
            reviewer_reply, _ = run_agent(
                client, REVIEWER_MODEL, REVIEWER_SYSTEM,
                reviewer_messages, REVIEWER_TOOLS, sandbox, log,
            )
            log(f"\n[Reviewer]\n{reviewer_reply}\n")

            # Step 4: 承認チェック
            if "APPROVED" in reviewer_reply:
                log(f"\n✅ Round {round_num} で承認されました！")
                break
        else:
            log(f"\n⚠️ {MAX_ROUNDS}ラウンドで承認に至りませんでした")

        # 成果物の出力
        log(f"\n{'='*60}")
        log("成果物:")
        log(f"{'='*60}")
        for file_path in sandbox.list_files():
            content = sandbox.read_file(file_path)
            log(f"\n--- {file_path} ---")
            log(content)

        log(f"\nWorkspace: {sandbox.workspace}")

    finally:
        log_file.close()
        print(f"\nログ保存先: logs/{timestamp}.txt")

    return sandbox


if __name__ == "__main__":
    goal = input("何を作りますか？ > ")
    if not goal.strip():
        goal = "電卓アプリをPythonで作ってください。四則演算と履歴表示機能付き。"
    sandbox = run_synapse(goal)
    print(f"\n成果物: {sandbox.workspace}")
