"""
Synapse - Minimal AI-to-AI Conversation
最小構成: Coder と Reviewer が会話してコードを完成させる
"""

import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-20250514"


def chat(system_prompt, messages):
    res = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    )
    return res.content[0].text


CODER_SYSTEM = """あなたは優秀なプログラマー「Coder」です。
- ユーザーの要望に対して、完全に動作するPythonコードを書いてください
- コードには必ずテスト（pytest形式）も含めてください
- コードブロック内にコードを書いてください"""

REVIEWER_SYSTEM = """あなたは厳格なコードレビュアー「Reviewer」です。
- コードの品質、バグ、テストの網羅性をチェックしてください
- 問題がなければ「APPROVED」とだけ返してください
- 問題があれば具体的な修正指示を出してください"""

MAX_ROUNDS = 5


def run(user_goal):
    print(f"\n{'='*60}")
    print(f"Goal: {user_goal}")
    print(f"{'='*60}\n")

    coder_messages = []
    reviewer_messages = []

    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"--- Round {round_num}/{MAX_ROUNDS} ---\n")

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
        print(f"[Coder]\n{coder_reply}\n")

        reviewer_messages.append({
            "role": "user",
            "content": f"以下のコードをレビューしてください:\n{coder_reply}",
        })

        reviewer_reply = chat(REVIEWER_SYSTEM, reviewer_messages)
        reviewer_messages.append({"role": "assistant", "content": reviewer_reply})
        print(f"[Reviewer]\n{reviewer_reply}\n")

        if "APPROVED" in reviewer_reply:
            print(f"✅ Round {round_num} で承認されました！\n")
            return coder_reply

    print(f"⚠️ {MAX_ROUNDS}ラウンドで承認に至りませんでした\n")
    return coder_reply


if __name__ == "__main__":
    goal = input("何を作りますか？ > ")
    if not goal.strip():
        goal = "じゃんけんゲームをPythonで作ってください。CUIで遊べるもの。"
    result = run(goal)
    print(f"\n{'='*60}")
    print("最終成果物:")
    print(f"{'='*60}")
    print(result)
