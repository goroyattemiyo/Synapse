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
    """CUI用: 従来のprint出力版"""
    result = run_synapse_with_callback(user_goal, callback=None)
    return result["sandbox"]


def run_synapse_with_callback(user_goal: str, callback=None) -> dict:
    """
    UI対応版: callbackでメッセージを通知する
    callback(agent: str, content: str) が呼ばれるたびにUIに反映
    """
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

    def notify(agent, content):
        log(f"[{agent}]\n{content}\n")
        if callback:
            callback(agent, content)

    log(f"{'='*60}")
    log(f"Synapse v0.3.1 - Multi-Agent System")
    log(f"Goal: {user_goal}")
    log(f"{'='*60}\n")

    result = {
        "sandbox": sandbox,
        "files": {},
        "approved": False,
        "rounds": 0,
        "log_path": f"logs/{timestamp}.txt",
    }

    try:
        # Step 1: Orchestrator
        notify("System", "Orchestrator が計画を作成中...")
        orch_messages = [{
            "role": "user",
            "content": f"以下のゴールの実装計画を簡潔に作成してください:\n\n{user_goal}",
        }]
        orch_reply, _ = run_agent(
            client, ORCHESTRATOR_MODEL, ORCHESTRATOR_SYSTEM,
            orch_messages, None, sandbox, log,
        )
        notify("Orchestrator", orch_reply)

        reviewer_reply = ""

        for round_num in range(1, MAX_ROUNDS + 1):
            result["rounds"] = round_num
            notify("System", f"--- Round {round_num}/{MAX_ROUNDS} ---")

            # Step 2: Coder
            notify("System", "Coder が実装中...")
            if round_num == 1:
                instruction = f"以下の計画に従って実装してください。ファイル数は最小限に:\n\n{orch_reply}"
            else:
                instruction = f"以下の指摘を修正してください。修正箇所のみ対応:\n\n{reviewer_reply}"

            coder_messages = [{"role": "user", "content": instruction}]
            coder_reply, _ = run_agent(
                client, CODER_MODEL, CODER_SYSTEM,
                coder_messages, CODER_TOOLS, sandbox, log,
            )
            notify("Coder", coder_reply)

            # Step 3: Reviewer
            notify("System", "Reviewer がレビュー中...")
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
            notify("Reviewer", reviewer_reply)

            if "APPROVED" in reviewer_reply:
                notify("System", f"Round {round_num} で承認されました!")
                result["approved"] = True
                break
        else:
            notify("System", f"{MAX_ROUNDS}ラウンドで承認に至りませんでした")

        # 成果物の収集
        for file_path in sandbox.list_files():
            content = sandbox.read_file(file_path)
            result["files"][file_path] = content
            log(f"\n--- {file_path} ---")
            log(content)

        log(f"\nWorkspace: {sandbox.workspace}")

    except Exception as e:
        notify("System", f"エラー: {str(e)}")
        result["error"] = str(e)
    finally:
        log_file.close()
        print(f"\nログ保存先: logs/{timestamp}.txt")

    return result


if __name__ == "__main__":
    goal = input("何を作りますか？ > ")
    if not goal.strip():
        goal = "電卓アプリをPythonで作ってください。四則演算と履歴表示機能付き。"
    result = run_synapse_with_callback(goal)
    print(f"\n成果物: {result['sandbox'].workspace}")
    print(f"承認: {result['approved']}")
    print(f"ラウンド: {result['rounds']}")
