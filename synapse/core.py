"""
Synapse Core Engine v0.3.1
改善版: トークン節約、Windows対応、ツール呼び出し制限
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
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            output = ""
            if result.stdout:
                output += result.stdout[:5000]
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr[:2000]}"
            output += f"\n[exit_code] {result.returncode}"
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
        "description": "Create or overwrite a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path. Example: src/main.py"},
                "content": {"type": "string", "description": "Complete file content."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command. Windows environment. Use 'dir' not 'ls'. Use 'python -m pytest' for tests. Timeout 60s.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Windows shell command."},
            },
            "required": ["command"],
        },
    },
]

CODER_TOOLS = TOOLS
REVIEWER_TOOLS = [TOOLS[1], TOOLS[2]]


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


# ===== エージェント実行 =====

def run_agent(client, model, system, messages, tools, sandbox, log_fn, max_iterations=20):
    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "system": system,
        "messages": list(messages),
    }
    if tools:
        kwargs["tools"] = tools

    for i in range(max_iterations):
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
                    log_fn(f"  [Result] {str(result)[:500]}")
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

ENV_CONTEXT = """
# 実行環境
- OS: Windows (cmd.exe)
- Python: 3.12
- Linuxコマンド(ls, find, head等)は使用不可。dir, type等を使うこと
- 文字コード: cp932環境。print文にUnicode記号(✓✗等)を使わないこと。ASCII文字のみ使うこと
- テスト実行: python -m pytest ファイル名 -v
"""

ORCHESTRATOR_SYSTEM = """あなたは Synapse の Orchestrator（指揮者）です。

# 責任
- ユーザーのゴールを分析し、簡潔な実装計画を作成する
- 必要なファイルは最小限にする（3ファイル以内が理想）
- ツールは使わない。判断と指示に専念する

# 出力フォーマット
**計画**: 1-2行で概要
**ファイル構成**: 作るファイル一覧（最小限）
**Coderへの指示**: 具体的な要件
**テスト方針**: テストすべきこと
""" + ENV_CONTEXT

CODER_SYSTEM = """あなたは Synapse の Coder（実装者）です。

# 責任
- Orchestrator の指示に従い、コードを書く
- write_file でファイルを作成し、run_command でテストを実行する

# 重要ルール
1. ファイル数は最小限にする（本体+テストの2ファイルが理想）
2. ツール呼び出しは1ターンで最大5回以内に抑える
3. 全コードを1回のwrite_fileで書き切る（分割しない）
4. テストは1回実行して結果を報告する
5. print文にUnicode記号を使わない。[OK], [FAIL]等のASCII文字を使う
6. Windowsコマンドのみ使用（dir, type等）
""" + ENV_CONTEXT

REVIEWER_SYSTEM = """あなたは Synapse の Reviewer（検証者）です。

# 責任
- Coder が作成したコードを検証する

# 重要ルール
1. read_file は主要ファイルのみ読む（最大3ファイル）
2. run_command でテストを1回実行する
3. ツール呼び出しは合計4回以内に抑える
4. 問題がなければ「APPROVED」と返す
5. 問題があれば最も重要な1-2点だけ指摘する（細かい指摘はしない）
6. 動作してテストが通っていればAPPROVEDとする
""" + ENV_CONTEXT


# ===== メインループ =====

MAX_ROUNDS = 3
MODEL = "claude-sonnet-4-20250514"


def run_synapse(user_goal):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    sandbox = Sandbox()

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
        # Step 1: Orchestrator
        log("[Orchestrator] 計画を作成中...\n")
        orch_messages = [{"role": "user", "content": f"以下のゴールの実装計画を簡潔に作成してください:\n\n{user_goal}"}]
        orch_reply, _ = run_agent(
            client, MODEL, ORCHESTRATOR_SYSTEM,
            orch_messages, None, sandbox, log
        )
        log(f"[Orchestrator]\n{orch_reply}\n")

        for round_num in range(1, MAX_ROUNDS + 1):
            log(f"\n{'='*40}")
            log(f"  Round {round_num}/{MAX_ROUNDS}")
            log(f"{'='*40}\n")

            # Step 2: Coder
            log("[Coder] 実装中...\n")
            if round_num == 1:
                coder_instruction = f"以下の計画に従って実装してください。ファイル数は最小限に:\n\n{orch_reply}"
            else:
                coder_instruction = f"以下の指摘を修正してください。修正箇所のみ対応:\n\n{reviewer_reply}"

            coder_messages = [{"role": "user", "content": coder_instruction}]
            coder_reply, _ = run_agent(
                client, MODEL, CODER_SYSTEM,
                coder_messages, CODER_TOOLS, sandbox, log
            )
            log(f"\n[Coder]\n{coder_reply}\n")

            # Step 3: Reviewer
            log("[Reviewer] レビュー中...\n")
            files = sandbox.list_files()
            reviewer_instruction = f"以下のファイルを検証してください。主要ファイルだけ読めばOK:\n{json.dumps(files, ensure_ascii=False)}\n\nテストが通っていればAPPROVEDとしてください。"
            reviewer_messages = [{"role": "user", "content": reviewer_instruction}]
            reviewer_reply, _ = run_agent(
                client, MODEL, REVIEWER_SYSTEM,
                reviewer_messages, REVIEWER_TOOLS, sandbox, log
            )
            log(f"\n[Reviewer]\n{reviewer_reply}\n")

            if "APPROVED" in reviewer_reply:
                log(f"\n✅ Round {round_num} で承認されました！")
                break
        else:
            log(f"\n⚠️ {MAX_ROUNDS}ラウンドで承認に至りませんでした")

        # 成果物
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
