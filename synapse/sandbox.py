"""
Synapse - サンドボックス
隔離されたワークスペースでファイル操作とコマンド実行を行う
"""

import subprocess
import os
import shutil
import tempfile
from pathlib import Path
from synapse.config import COMMAND_TIMEOUT, MAX_FILE_READ_SIZE, STDOUT_LIMIT, STDERR_LIMIT


class Sandbox:
    def __init__(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="synapse_"))

    def write_file(self, path: str, content: str) -> str:
        file_path = self.workspace / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"

    def read_file(self, path: str) -> str:
        file_path = self.workspace / path
        if not file_path.exists():
            return f"Error: {path} not found"
        content = file_path.read_text(encoding="utf-8")
        if len(content) > MAX_FILE_READ_SIZE:
            return content[:MAX_FILE_READ_SIZE] + "\n...(truncated)"
        return content

    def run_command(self, command: str) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            output = ""
            if result.stdout:
                output += result.stdout[:STDOUT_LIMIT]
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr[:STDERR_LIMIT]}"
            output += f"\n[exit_code] {result.returncode}"
            return output
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out ({COMMAND_TIMEOUT}s)"
        except Exception as e:
            return f"Error: {e}"

    def list_files(self) -> list:
        files = []
        for f in self.workspace.rglob("*"):
            if f.is_file():
                files.append(str(f.relative_to(self.workspace)))
        return files

    def cleanup(self):
        shutil.rmtree(self.workspace, ignore_errors=True)
