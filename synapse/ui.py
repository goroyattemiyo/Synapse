"""
Synapse - Streamlit UI
LINE風チャット画面でエージェント会話をリアルタイム表示
"""
import streamlit as st
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Synapse - AI Agent System",
    page_icon="🧠",
    layout="wide"
)

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
    background-color: #f3e5f5;
    border-radius: 15px;
    padding: 8px 15px;
    margin: 5px auto;
    max-width: 60%;
    text-align: center;
    font-size: 0.9em;
    color: #6a1b9a;
}
.msg-user {
    background-color: #e1f5fe;
    border-radius: 15px;
    padding: 10px 15px;
    margin: 5px 0;
    max-width: 80%;
    margin-left: auto;
    border-right: 4px solid #0288d1;
}
.agent-name {
    font-weight: bold;
    font-size: 0.85em;
    margin-bottom: 4px;
}
.msg-content {
    white-space: pre-wrap;
    word-wrap: break-word;
}
.timestamp {
    font-size: 0.7em;
    color: #999;
    text-align: right;
    margin-top: 4px;
}
.status-bar {
    background-color: #263238;
    color: #4fc3f7;
    padding: 8px 15px;
    border-radius: 5px;
    font-family: monospace;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

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
if "approved" not in st.session_state:
    st.session_state.approved = False

def add_message(agent, content, msg_type="text"):
    st.session_state.messages.append({
        "agent": agent,
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "type": msg_type
    })

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_messages_html():
    icon_map = {
        "Orchestrator": "🎯", "Coder": "💻",
        "Reviewer": "🔍", "System": "⚙️", "User": "👤"
    }
    class_map = {
        "Orchestrator": "msg-orchestrator", "Coder": "msg-coder",
        "Reviewer": "msg-reviewer", "System": "msg-system", "User": "msg-user"
    }
    html = '<div class="chat-container">'
    for msg in st.session_state.messages:
        agent = msg["agent"]
        css = class_map.get(agent, "msg-system")
        icon = icon_map.get(agent, "💬")
        content = escape_html(msg["content"])
        if len(content) > 500:
            content = content[:500] + "..."
        if agent == "System":
            html += f'<div class="{css}">{icon} {content} <span class="timestamp">{msg["timestamp"]}</span></div>'
        else:
            html += f'<div class="{css}"><div class="agent-name">{icon} {agent}</div><div class="msg-content">{content}</div><div class="timestamp">{msg["timestamp"]}</div></div>'
    html += '</div>'
    return html

st.title("🧠 Synapse")
st.caption("Multi-AI Agent Collaborative Development System")

status_icon = {"待機中": "⏸", "実行中": "▶", "完了": "✅", "完了 (デモ)": "🎭", "エラー": "❌"}.get(st.session_state.status, "⏸")
st.markdown(
    f'<div class="status-bar">{status_icon} Status: {st.session_state.status} | Round: {st.session_state.round_num}/3 | Messages: {len(st.session_state.messages)}</div>',
    unsafe_allow_html=True
)

col_chat, col_artifacts = st.columns([3, 2])

with col_chat:
    st.subheader("💬 Agent Discussion")
    st.markdown(render_messages_html(), unsafe_allow_html=True)
    st.divider()
    goal = st.text_area("何を作りますか？", placeholder="例: 電卓アプリをPythonで作ってください", height=80, disabled=st.session_state.running)
    col_run, col_stop, col_clear = st.columns(3)
    with col_run:
        run_btn = st.button("🚀 実行", type="primary", use_container_width=True, disabled=st.session_state.running)
    with col_stop:
        stop_btn = st.button("⏹ 停止", use_container_width=True)
    with col_clear:
        clear_btn = st.button("🗑 クリア", use_container_width=True)

with col_artifacts:
    st.subheader("📁 Artifacts")
    if st.session_state.files:
        for filename, content in st.session_state.files.items():
            with st.expander(f"📄 {filename}", expanded=False):
                lang = "python" if filename.endswith(".py") else "text"
                st.code(content, language=lang)
        import io, zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, fcontent in st.session_state.files.items():
                zf.writestr(fname, fcontent)
        zip_buffer.seek(0)
        st.download_button(label="📦 ZIP ダウンロード", data=zip_buffer, file_name="synapse_output.zip", mime="application/zip", use_container_width=True)
    else:
        st.info("実行するとここに成果物が表示されます")
    st.subheader("📊 Log")
    if st.session_state.messages:
        log_text = "\n".join(f"[{m['timestamp']}] {m['agent']}: {m['content'][:80]}" for m in st.session_state.messages)
        st.text_area("", value=log_text, height=200, disabled=True, label_visibility="collapsed")
    else:
        st.info("ログはここに表示されます")

if clear_btn:
    st.session_state.messages = []
    st.session_state.files = {}
    st.session_state.round_num = 0
    st.session_state.status = "待機中"
    st.session_state.approved = False
    st.rerun()

if run_btn and goal.strip():
    st.session_state.status = "実行中"
    st.session_state.running = True
    add_message("User", goal.strip())
    add_message("System", "Synapse を起動しました")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or "ここに" in api_key:
        add_message("System", "デモモード: APIキー未設定")
        st.session_state.round_num = 1
        add_message("Orchestrator", "計画: " + goal.strip() + "\n\nファイル構成:\n- main.py\n- test_main.py\n\nCoderへ: 実装を開始してください。")
        add_message("Coder", "実装を完了しました。\n- main.py (作成済み)\n- test_main.py (作成済み)\n- テスト全件パス")
        add_message("Reviewer", "APPROVED\n\nコード品質、テストカバレッジともに問題ありません。")
        st.session_state.files = {
            "main.py": "# Generated by Synapse\nprint('Hello from Synapse!')",
            "test_main.py": "import unittest\n\nclass TestMain(unittest.TestCase):\n    def test_example(self):\n        self.assertTrue(True)\n\nif __name__ == '__main__':\n    unittest.main()"
        }
        st.session_state.status = "完了 (デモ)"
        st.session_state.approved = True
    else:
        add_message("System", "Anthropic API に接続中...")
        try:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from synapse.engine import run_synapse_with_callback
            def on_message(agent, content):
                add_message(agent, content)
            result = run_synapse_with_callback(goal.strip(), on_message)
            if result.get("files"):
                st.session_state.files = result["files"]
            st.session_state.round_num = result.get("rounds", 0)
            st.session_state.approved = result.get("approved", False)
            st.session_state.status = "完了" if result.get("approved") else "完了 (未承認)"
        except Exception as e:
            add_message("System", f"エラー: {str(e)}")
            st.session_state.status = "エラー"
    st.session_state.running = False
    st.rerun()

st.divider()
st.caption("Synapse v0.3.1 | Powered by Anthropic Claude")
