# loop-engineer

Conversation-driven autonomous GitHub incubator and progressive commit engine (`hd`).

`loop-engineer` continuously observes daily human-agent problem solving (debugging logs, architectural discussions, friction points, and cognitive models) and turns those insights into clean, tested, privacy-safe open-source repositories.

## Architecture

1. **Multi-Source Collector (`loop_engineer/collector.py`)**
   Polls local engineering artifacts (conversation ledgers, debugging playbooks, thought diaries, and agent session transcripts) with zero idle token overhead.
2. **Persona & Pillar Filter (`loop_engineer/persona.py`)**
   Routes every extracted signal into one of four core engineering pillars:
   - `workflow-mcp`: Campus, media, and network workflow automation & MCP bridges
   - `ai-infra-harness`: Rolling-window LLM quota routing, prompt-cache affinity, and multi-agent harness sync
   - `quant-fintech-web3`: EVM delta-neutral vaults, perpetuals funding-rate microstructure, and Byzantine-resilient FL
   - `cognitive-systems`: Executable models for transaction-cost economics and stylometry
3. **Zero-Leak Privacy Gate (`loop_engineer/privacy.py`)**
   Enforces pre-commit redaction across all staged files, blocking API keys, personal identifiers, student IDs, and private infrastructure endpoints before any commit reaches Git.
4. **Dual-Pool Progressive Planner (`loop_engineer/planner.py`)**
   Combines a 7-day flagship repository schedule with dynamic conversation signals, ensuring 2-4 high-signal, test-verified commits every day even on days without new conversations.
5. **Blank-Account GitHub Binder (`loop_engineer/github_sync.py`)**
   Supports offline progressive commits and retroactive Git author normalization (`user.name` / `user.email`) when binding a fresh GitHub account.

## Quickstart

```bash
# 1. Run test suite
pytest -q

# 2. Poll local conversations & inspect next milestone
python3 loop.py status

# 3. View the 7-day flagship repository plan
python3 loop.py plan

# 4. Start the detached background daemon (polls every hour)
python3 loop.py daemon --interval 3600 --detach

# 5. Bind a new GitHub account, normalize commit authors, and push all repos
python3 loop.py bind-github --login-web --username <NEW_GITHUB_USER> --push
```
