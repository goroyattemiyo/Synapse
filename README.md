cat > README.md << 'ENDOFFILE'
# 🧠 Synapse

**Multi-AI Agent Collaborative Development System**

AI エージェント同士が議論・設計・実装・テスト・修正し、動作確認済みコードを返すシステム。

## Overview

ユーザーが自然言語でゴールを伝えると、3体の AI エージェントが協調してコードを生成します。

| Agent | Role | Model |
|-------|------|-------|
| 🎯 Orchestrator | 計画・指揮 | Claude Sonnet 4 |
| 💻 Coder | 実装・テスト | Claude Sonnet 4 |
| 🔍 Reviewer | 検証・承認 | Claude Sonnet 4 |

## Architecture

User Goal → Orchestrator(計画) → Coder(実装) → Reviewer(検証) ↑ | └── 修正指示 ──┘ (最大3ラウンド)


## Project Structure

synapse/ ├── config.py # モデル・制限値の設定 ├── sandbox.py # ファイル操作・コマンド実行 ├── tools.py # Anthropic Tool Use API 定義 ├── prompts.py # エージェント別システムプロンプト ├── agents.py # ツールループ管理 ├── engine.py # メインエンジン（Orchestrator→Coder→Reviewer） └── ui.py # Streamlit UI（LINE風チャット） docs/ └── design_v0.3.md # 設計書


## Quick Start

### 1. Clone

```bash
git clone https://github.com/goroyattemiyo/Synapse.git
cd Synapse
2. Install
Copypip install anthropic python-dotenv streamlit
3. Set API Key
Copyecho "ANTHROPIC_API_KEY=sk-ant-your-key" > .env
4. Run (CUI)
Copypython -m synapse.engine
5. Run (Web UI)
Copystreamlit run synapse/ui.py
Performance
Task	Rounds	Cost	Time
電卓アプリ	1	$0.22	~2 min
じゃんけんゲーム	1	$0.29	~2 min
ローグライクダンジョン	4 (未承認)	$2.94	~10 min
Design Principles
Human Sovereignty - ユーザーが最終承認・中断権限を保持
Transparency - 全エージェント会話を閲覧可能
Minimum Viable Agent - 3体構成で最大効果
Design for Failure - タイムアウト・トークン枯渇を前提に設計
Economic Viability - トークン消費上限で自動停止
Tech Stack
Python 3.12
Anthropic Claude API (Tool Use)
Streamlit (Web UI)
Docker (Sandbox - planned)
Status
🟢 MVP Phase - Core engine working, Streamlit UI connected

License
MIT ENDOFFILE