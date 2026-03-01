"""
Synapse - ツール定義と実行
"""

from synapse.sandbox import Sandbox

# ツール定義（Anthropic Tool Use API 形式）

WRITE_FILE = {
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
}

READ_FILE = {
    "name": "read_file",
    "description": "Read a file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read."},
        },
        "required": ["path"],
    },
}

RUN_COMMAND = {
    "name": "run_command",
    "description": "Run a shell command. Windows env. Use 'dir' not 'ls'. Timeout 60s.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Windows shell command."},
        },
        "required": ["command"],
    },
}

# エージェント別ツールセット
CODER_TOOLS = [WRITE_FILE, READ_FILE, RUN_COMMAND]
REVIEWER_TOOLS = [READ_FILE, RUN_COMMAND]  # 書き込み権限なし


def execute_tool(sandbox: Sandbox, name: str, input_data: dict) -> str:
    if name == "write_file":
        return sandbox.write_file(input_data["path"], input_data["content"])
    elif name == "read_file":
        return sandbox.read_file(input_data["path"])
    elif name == "run_command":
        return sandbox.run_command(input_data["command"])
    else:
        return f"Unknown tool: {name}"
