"""
Synapse - Streamlit UI
LINE風チャット画面でエージェント会話をリアルタイム表示
"""
import streamlit as st
import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ページ設定
st.set_page_config(
    page_title="Synapse - AI Agent System",
    page_icon="🧠",
    layout="wide"
)

# カスタムCSS - LINE風チャットUI
st.markdown("""
<style>
.chat-container {
    max-height: 500px;
    overflow-y: auto;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 10px;
    background-color: #f5f5f5;
}
.msg-orchestrator {
    background-color: #e3f2fd;
    border-radius: 15px;
    padding: 10px 15px;
    margin: 5px 0;
    max-width: 80%;
    border-left: 4px solid #1976d2;
}
.msg-coder {
    background-color: #e8f5e9;
    border-radius: 15px;
    padding: 10px 15px;
    margin: 5px 0;
    max-width: 80%;
    margin-left: auto;
    border-right: 4px solid #388e3c;
}
.msg-reviewer {
    background-color: #fff3e0;
    border-radius: 15px;
    padding: 10px 15px;
    margin: 5px 0;
    max-width: 80%;
    border-left: 4px solid #f57c00;
}
.msg-system {
    background-color: #fce4ec;
    border-radius: 15px;
    padding: 10px 15px;
    margin: 5px 0;
    max-width: 80%;
    text-align: center;
    margin-left: auto;
    margin-right: auto;
}
.agent-name {
    font-weight: bold;
    font-size: 0.85em;
    margin-bottom: 4px;
}
.timestamp {
    font-size: 0.7em;
    color: #999;
    text-align: right;
}
.status-bar {
    background-color: #263238;
    color: white;
    padding: 8px 15px;
    border-radius: 5px;
    font-family: monospace;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "running" not in st.session_state:
    st.session_state.running = False
if "files" not in st.session_state:
    st.session_state.files = {}
if "round_num" not in st.session_state:
    st.session_state.round_num = 0
if "status" not in st.session_state:
    st.session_state.status = "待機中"

def add_message(agent, content, msg_type="text"):
    st.session_state.messages.append({
        "agent": agent,
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "type": msg_type
    })

def render_message(msg):
    agent = msg["agent"]
    css_class = {
        "Orchestrator": "msg-orchestrator",
        "Coder": "msg-coder",
        "Reviewer": "msg-reviewer",
        "System": "msg-system",
        "User": "msg-system"
    }.get(agent, "msg-system")

    icon = {
        "Orchestrator": "🎯",
        "Coder": "💻",
        "Reviewer": "🔍",
        "System": "⚙️",
        "User": "👤"
    }.get(agent, "💬")

    return f"""
    <div class="{css_class}">
        <div class="agent-name">{icon} {agent}</div>
        <div>{msg["content"][:500]}{"..." if len(msg["content"]) > 500 else ""}</div>
        <div class="timestamp">{msg["timestamp"]}</div>
    </div>
    """

# ヘッダー
st.title("🧠 Synapse")
st.caption("Multi-AI Agent Collaborative Development System")

# ステータスバー
st.markdown(
    f'<div class="status-bar">Status: {st.session_state.status} | '
    f'Round: {st.session_state.round_num}/3 | '
    f'Messages: {len(st.session_state.messages)}</div>',
    unsafe_allow_html=True
)

# メインレイアウト: 左=チャット、右=成果物
col_chat, col_artifacts = st.columns([3, 2])

with col_chat:
    st.subheader("💬 Agent Discussion")

    # チャット表示エリア
    chat_html = '<div class="chat-container">'
    for msg in st.session_state.messages:
        chat_html += render_message(msg)
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # 入力エリア
    st.divider()
    goal = st.text_area(
        "何を作りますか？",
        placeholder="例: 電卓アプリをPythonで作ってください",
        height=80
    )

    col_run, col_stop, col_clear = st.columns(3)
    with col_run:
        run_btn = st.button("🚀 実行", type="primary", use_container_width=True)
    with col_stop:
        stop_btn = st.button("⏹ 停止", use_container_width=True)
    with col_clear:
        clear_btn = st.button("🗑 クリア", use_container_width=True)

with col_artifacts:
    st.subheader("📁 Artifacts")

    if st.session_state.files:
        for filename, content in st.session_state.files.items():
            with st.expander(f"📄 {filename}", expanded=False):
                st.code(content, language="python")

        # ZIPダウンロード
        import io, zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, fcontent in st.session_state.files.items():
                zf.writestr(fname, fcontent)
        zip_buffer.seek(0)
        st.download_button(
            label="📦 ZIP Download",
            data=zip_buffer,
            file_name="synapse_output.zip",
            mime="application/zip",
            use_container_width=True
        )
    else:
        st.info("実行するとここに成果物が表示されます")

    # ログ表示
    st.subheader("📊 Log")
    if st.session_state.messages:
        log_text = "\n".join(
            f"[{m['timestamp']}] {m['agent']}: {m['content'][:100]}"
            for m in st.session_state.messages
        )
        st.text_area("", value=log_text, height=200, disabled=True)

# ボタン処理
if clear_btn:
    st.session_state.messages = []
    st.session_state.files = {}
    st.session_state.round_num = 0
    st.session_state.status = "待機中"
    st.rerun()

if run_btn and goal.strip():
    st.session_state.status = "実行中"
    st.session_state.running = True
    add_message("User", goal.strip())
    add_message("System", "Synapse を起動しました。エージェントが作業を開始します...")

    # デモモード: API未接続時のシミュレーション
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "sk-ant-ここにフルキーを貼る":
        add_message("System", "⚠ デモモード: APIキーが未設定のため、サンプル表示します")
        st.session_state.round_num = 1

        add_message("Orchestrator",
            f"計画: {goal.strip()}\n\n"
            "ファイル構成:\n"
            "- main.py (メインアプリ)\n"
            "- test_main.py (テスト)\n\n"
            "Coderへ: 上記の実装を開始してください。")

        add_message("Coder",
            "実装を完了しました。\n\n"
            "- main.py (作成済み)\n"
            "- test_main.py (作成済み)\n"
            "- テスト全件パス")

        add_message("Reviewer", "APPROVED\n\nコード品質、テストカバレッジともに問題ありません。")

        st.session_state.files = {
            "main.py": "# Generated by Synapse\\nprint('Hello from Synapse!')",
            "test_main.py": "# Tests\\nimport unittest\\n\\nclass TestMain(unittest.TestCase):\\n    def test_example(self):\\n        self.assertTrue(True)"
        }
        st.session_state.status = "完了 (デモ)"
    else:
        # 実際のエンジン実行
        add_message("System", "Anthropic API に接続中...")
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from synapse.engine import run_synapse_with_callback

            def on_message(agent, content):
                add_message(agent, content)

            result = run_synapse_with_callback(goal.strip(), on_message)
            if result and result.get("files"):
                st.session_state.files = result["files"]
            st.session_state.status = "完了"
        except ImportError:
            add_message("System", "エンジン接続準備中。現在はデモモードで表示しています。")
            st.session_state.status = "完了 (デモ)"
        except Exception as e:
            add_message("System", f"エラー: {str(e)}")
            st.session_state.status = "エラー"

    st.session_state.running = False
    st.rerun()

# フッター
st.divider()
st.caption("Synapse v0.3.1 | Powered by Anthropic Claude")
