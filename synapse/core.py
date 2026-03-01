"""
Synapse Core Engine
Orchestrator・Coder・Reviewer の3エージェント構成
Anthropic Tool Use API を使用
"""

import anthropic
import subprocess
import json
import time
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ===== サンドボックス =====

class Sandbox:
    def __init__(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="synapse_"))
        print(f"[Sandbox] Workspace: {self.workspace}")

    def write_file(self, path, content):
        file_path = self.workspace / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"

    def read_file(self, path):
        file_path = self.workspace / path
        if not file_path.exists():
            return f"Error: {path} not found"
        content = file_path.read_text(encoding="utf-8")
        if len(content) > 100_000:
            return content[:100_000] + "\n...(truncated)"
        return content

    def run_command(self, command):
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = ""
            if result.stdout:
                output += f"[stdout]\n{result.stdout}\n"
            if result.stderr:
                output += f"[stderr]\n{result.stderr}\n"
            output += f"[exit_code] {result.returncode}"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out (60s)"
        except Exception as e:
            return f"Error: {e}"

    def list_files(self):
        files = []
        for f in self.workspace.rglob("*"):
            if f.is_file():
                files.append(str(f.relative_to(self.workspace)))
        return files

    def cleanup(self):
        shutil.rmtree(self.workspace, ignore_errors=True)


# ===== ツール定義 =====

TOOLS = [
    {
        "name": "write_file",
        "description": "Create or overwrite a file. Use for writing code, tests, configs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace root. Example: src/main.py"},
                "content": {"type": "string", "description": "Complete file content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read. Example: src/main.py"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command in the workspace. Timeout 60s. Use for running tests, installing packages, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command. Example: python -m pytest tests/ -v"},
            },
            "required": ["command"],
        },
    },
]

CODER_TOOLS = TOOLS  # write, read, run
REVIEWER_TOOLS = [TOOLS[1], TOOLS[2]]  # read, run のみ


# ===== ツール実行 =====

def execute_tool(sandbox, name, input_data):
    if name == "write_file":
        return sandbox.write_file(input_data["path"], input_data["content"])
    elif name == "read_file":
        return sandbox.read_file(input_data["path"])
    elif name == "run_command":
        return sandbox.run_command(input_data["command"])
    else:
        return f"Unknown tool: {name}"


# ===== エージェント呼び出し =====

def call_agent(client, model, system, messages, tools=None, max_iterations=10):
    """
    エージェントを呼び出し、ツールループを回す。
    Claude が tool_use を返す限りツールを実行して結果を返す。
    テキスト応答が返ったらループ終了。
    """
    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools

    for _ in range(max_iterations):
        response = client.messages.create(**kwargs)

        # テキストのみの応答 → 終了
        if response.stop_reason == "end_turn":
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
            return text, messages

        # ツール呼び出し
        if response.stop_reason == "tool_use":
            # assistant の応答をメッセージに追加
            messages.append({"role": "assistant", "content": response.content})

            # ツール結果を収集
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = yield block.name, block.input
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })

            messages.append({"role": "user", "content": tool_results})
            kwargs["messages"] = messages
        else:
            # その他の stop_reason
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
            return text, messages

    return "Error: max iterations reached", messages


def run_agent(client, model, system, messages, tools, sandbox, log_fn):
    """
    call_agent のジェネレータを駆動し、ツール実行を行う。
    """
    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": list(messages),
    }
    if tools:
        kwargs["tools"] = tools

    for _ in range(10):
        response = client.messages.create(**kwargs)

        if response.stop_reason == "end_turn":
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
            return text, kwargs["messages"]

        if response.stop_reason == "tool_use":
            kwargs["messages"].append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    log_fn(f"  [Tool] {block.name}({json.dumps(block.input, ensure_ascii=False)[:200]})")
                    result = execute_tool(sandbox, block.name, block.input)
                    log_fn(f"  [Result] {str(result)[:300]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })

            kwargs["messages"].append({"role": "user", "content": tool_results})
        else:
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text
            return text, kwargs["messages"]

    return "Error: max tool iterations reached", kwargs["messages"]


# ===== システムプロンプト =====

ORCHESTRATOR_SYSTEM = """あなたは Synapse の Orchestrator（指揮者）です。

# 責任
- ユーザーのゴールを分析し、実装計画を作成する
- Coder への具体的な実装指示を出す
- Reviewer のフィードバックを解釈し、次のアクションを決定する
- ツールは使わない。判断と指示に専念する

# 出力フォーマット
**計画**: 何をどう実装するか
**Coderへの指示**: 具体的なファイル構成とコード要件
**テスト方針**: 何をテストすべきか"""

CODER_SYSTEM = """あなたは Synapse の Coder（実装者）です。

# 責任
- Orchestrator の指示に従い、コードを書く
- テストも書く
- ツールを使ってファイルを作成し、テストを実行する
- 結果を報告する

# ルール
1. write_file でファイルを作成すること
2. run_command でテストを実行すること
3. テストが通るまで修正すること
4. 簡潔に、動くコードを書くこと
5. 日本語のコメントを入れること"""

REVIEWER_SYSTEM = """あなたは Synapse の Reviewer（検証者）です。

# 責任
- Coder が作成したコードを read_file で読む
- run_command でテストを実行して確認する
- 品質、バグ、テスト網羅性をチェックする

# ルール
1. 必ず read_file と run_command を使って実際に確認すること
2. 問題がなければ「APPROVED」と返すこと
3. 問題があれば具体的な修正指示を出すこと
4. ファイルの書き込みはしないこと（読み取り専用）"""


# ===== メインループ =====

MAX_ROUNDS = 5
ORCHESTRATOR_MODEL = "claude-sonnet-4-20250514"
CODER_MODEL = "claude-sonnet-4-20250514"
REVIEWER_MODEL = "claude-sonnet-4-20250514"


def run_synapse(user_goal):
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
    log(f"Synapse v0.3 - Multi-Agent System")
    log(f"Goal: {user_goal}")
    log(f"{'='*60}\n")

    try:
        # Step 1: Orchestrator が計画を立てる
        log("[Orchestrator] 計画を作成中...\n")
        orch_messages = [{"role": "user", "content": f"以下のゴールに対する実装計画を作成してください:\n\n{user_goal}"}]
        orch_reply, orch_messages = run_agent(
            client, ORCHESTRATOR_MODEL, ORCHESTRATOR_SYSTEM,
            orch_messages, None, sandbox, log
        )
        log(f"[Orchestrator]\n{orch_reply}\n")

        for round_num in range(1, MAX_ROUNDS + 1):
            log(f"\n{'='*40}")
            log(f"  Round {round_num}/{MAX_ROUNDS}")
            log(f"{'='*40}\n")

            # Step 2: Coder が実装
            log("[Coder] 実装中...\n")
            if round_num == 1:
                coder_instruction = f"Orchestratorの計画に従って実装してください:\n\n{orch_reply}"
            else:
                coder_instruction = f"Reviewerから以下の指摘がありました。修正してください:\n\n{reviewer_reply}"

            coder_messages = [{"role": "user", "content": coder_instruction}]
            coder_reply, coder_messages = run_agent(
                client, CODER_MODEL, CODER_SYSTEM,
                coder_messages, CODER_TOOLS, sandbox, log
            )
            log(f"\n[Coder]\n{coder_reply}\n")

            # Step 3: Reviewer が検証
            log("[Reviewer] レビュー中...\n")
            files = sandbox.list_files()
            reviewer_instruction = f"Coderが以下のファイルを作成しました:\n{json.dumps(files, ensure_ascii=False)}\n\nread_file と run_command を使って検証してください。"
            reviewer_messages = [{"role": "user", "content": reviewer_instruction}]
            reviewer_reply, reviewer_messages = run_agent(
                client, REVIEWER_MODEL, REVIEWER_SYSTEM,
                reviewer_messages, REVIEWER_TOOLS, sandbox, log
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
