# Synapse

**Multi-AI Agent Collaborative Development System**

AI エージェント同士が議論・設計・実装・テスト・修正し、動作確認済みコードを返すシステム。

## Overview

ユーザーが自然言語でゴールを伝えると、3体のAIエージェントが協調してコードを生成します。

| Agent | Role | Model |
|-------|------|-------|
| Orchestrator | 計画・指揮 | Claude Sonnet 4 |
| Coder | 実装・テスト | Claude Sonnet 4 |
| Reviewer | 検証・承認 | Claude Sonnet 4 |

## Architecture

User Goal → Orchestrator(計画) → Coder(実装) → Reviewer(検証) → 承認 or 修正ループ(最大3ラウンド)

## Quick Start

1. git clone https://github.com/goroyattemiyo/Synapse.git
2. cd Synapse
3. pip install anthropic python-dotenv streamlit
4. echo "ANTHROPIC_API_KEY=your-key" > .env
5. CUI: python -m synapse.engine
6. Web UI: streamlit run synapse/ui.py

## Performance

| Task | Rounds | Cost |
|------|--------|------|
| Calculator | 1 | $0.22 |
| Janken Game | 1 | $0.29 |

## Design Principles

1. Human Sovereignty
2. Transparency
3. Minimum Viable Agent
4. Design for Failure
5. Economic Viability

## Tech Stack

Python 3.12 / Anthropic Claude API / Streamlit / Docker (planned)

## License

MIT