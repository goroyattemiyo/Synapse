"""
Synapse - Minimal AI-to-AI Conversation
設計書を読み込んでコンテキストとして渡す版
"""

import anthropic
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"

LOG_FILE = None

# 設計書を読み込む
DESIGN_DOC = ""
design_path = "docs/design_v0.3.md"
if os.path.exists(design_path):
    with open(design_path, "r", encoding="utf-8") as f:
        DESIGN_DOC = f.read()


def log(text):
    print(text)
    if LOG_FILE:
        LOG_FILE.write(text + "\n")


def chat(system_prompt, messages):
    res = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    )
    return res.content[0].text


CODER_SYSTEM = f"""あなたは優秀なプログラマー「Coder」です。
- ユーザーの要望に対して、完全に動作するPythonコードを書いてください
- コードには必ずテスト（pytest形式）も含めてください
- コードブロック内にコードを書いてください
- 出力が途切れないよう、簡潔に書いてください

以下はプロジェクトの設計書です。この設計に従って実装してください：

<design_document>
{DESIGN_DOC}
</design_document>"""

REVIEWER_SYSTEM = f"""あなたは厳格なコードレビュアー「Reviewer」です。
- コードの品質、バグ、テストの網羅性をチェックしてください
- 問題がなければ「APPROVED」とだけ返してください
- 問題があれば具体的な修正指示を簡潔に出してください

以下はプロジェクトの設計書です。この設計に準拠しているかもチェックしてください：

<design_document>
{DESIGN_DOC}
</design_document>"""

MAX_ROUNDS = 5


def run(user_goal):
    log(f"\n{'='*60}")
    log(f"Goal: {user_goal}")
    log(f"{'='*60}\n")

    coder_messages = []
    reviewer_messages = []

    for round_num in range(1, MAX_ROUNDS + 1):
        log(f"--- Round {round_num}/{MAX_ROUNDS} ---\n")

        if round_num == 1:
            coder_messages.append({
                "role": "user",
                "content": f"以下を実装してください:\n{user_goal}",
            })
        else:
            coder_messages.append({
                "role": "user",
                "content": f"Reviewerから以下の指摘がありました。修正してください:\n{reviewer_reply}",
            })

        coder_reply = chat(CODER_SYSTEM, coder_messages)
        coder_messages.append({"role": "assistant", "content": coder_reply})
        log(f"[Coder]\n{coder_reply}\n")

        reviewer_messages.append({
            "role": "user",
            "content": f"以下のコードをレビューしてください:\n{coder_reply}",
        })

        reviewer_reply = chat(REVIEWER_SYSTEM, reviewer_messages)
        reviewer_messages.append({"role": "assistant", "content": reviewer_reply})
        log(f"[Reviewer]\n{reviewer_reply}\n")

        if "APPROVED" in reviewer_reply:
            log(f"✅ Round {round_num} で承認されました！\n")
            return coder_reply

    log(f"⚠️ {MAX_ROUNDS}ラウンドで承認に至りませんでした\n")
    return coder_reply


if __name__ == "__main__":
    goal = input("何を作りますか？ > ")
    if not goal.strip():
        goal = "じゃんけんゲームをPythonで作ってください。CUIで遊べるもの。"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"logs/{timestamp}.txt"
    LOG_FILE = open(log_path, "w", encoding="utf-8")

    result = run(goal)
    log(f"\n{'='*60}")
    log("最終成果物:")
    log(f"{'='*60}")
    log(result)

    LOG_FILE.close()
    print(f"\nログ保存先: {log_path}")
