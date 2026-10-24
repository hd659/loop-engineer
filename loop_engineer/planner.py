"""
Dual-Pool Backlog & 7-Day Progressive Schedule Engine.

Implements Refined Mode (精耕模式):
- Focuses on 5 high-leverage flagship repositories over a 7-day rolling window
- Breaks each repository into granular, testable daily milestones (2-4 commits/day)
- Dynamically folds newly collected conversation signals into matching repositories
  so daily chats continuously enrich the GitHub portfolio without creating empty toy repos.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from .collector import EngineeringSignal


@dataclass
class CommitMilestone:
    milestone_id: str
    commit_type: str  # e.g. "feat", "test", "perf", "docs"
    scope: str
    summary: str
    deliverables: List[str]
    status: str = "pending"  # "pending" | "completed"
    committed_at: Optional[str] = None


@dataclass
class PlannedProject:
    repo_name: str
    pillar: str
    tagline: str
    origin_context: str
    scheduled_days: List[str]
    tech_stack: List[str]
    milestones: List[CommitMilestone] = field(default_factory=list)
    dynamic_signals: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


def build_default_weekly_projects() -> List[PlannedProject]:
    """Construct the initial 7-day flagship project lineup grounded in Haodong's history."""
    return [
        PlannedProject(
            repo_name="loop-engineer",
            pillar="ai-infra-harness",
            tagline="Conversation-driven autonomous GitHub incubator & progressive commit engine.",
            origin_context=(
                "Originates from Haodong's need to bridge high-velocity multi-agent problem solving "
                "with a consistent, high-signal GitHub engineering portfolio via automated loop engineering."
            ),
            scheduled_days=["2026-10-25 (Day 1)"],
            tech_stack=["Python", "PyTest", "GitHub CLI", "AgentAPI", "Launchd"],
            milestones=[
                CommitMilestone(
                    milestone_id="le-m1",
                    commit_type="feat",
                    scope="core",
                    summary="implement persona filter, zero-leak privacy gate, and multi-source collector",
                    deliverables=["loop_engineer/persona.py", "loop_engineer/privacy.py", "loop_engineer/collector.py"],
                ),
                CommitMilestone(
                    milestone_id="le-m2",
                    commit_type="feat",
                    scope="scheduler",
                    summary="add dual-pool 7-day planner, blank-account GitHub binder, and autonomous daemon",
                    deliverables=["loop_engineer/planner.py", "loop_engineer/github_sync.py", "loop_engineer/daemon.py", "loop.py"],
                ),
                CommitMilestone(
                    milestone_id="le-m3",
                    commit_type="test",
                    scope="suite",
                    summary="add unit tests for privacy redaction, signal classification, and milestone state machine",
                    deliverables=["tests/test_loop_engineer.py", "README.md", "WEEKLY_PLAN.md"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="uni-lms-mcp-suite",
            pillar="workflow-mcp",
            tagline="Privacy-safe University LMS (Moodle + Ed Discussion + Campus Mail) MCP automation suite.",
            origin_context=(
                "Distilled from building moodle-mcp, edstem-mcp, and monash-mail-mcp to eliminate manual "
                "attendance code hunting, cross-timezone deadline miscalculations (AEDT vs MYT), and Claude Draft 2020-12 anyOf schema errors."
            ),
            scheduled_days=["2026-10-26 (Day 2)", "2026-10-28 (Day 4)"],
            tech_stack=["Python", "FastMCP", "AsyncIO", "JSON-Schema"],
            milestones=[
                CommitMilestone(
                    milestone_id="lms-m1",
                    commit_type="feat",
                    scope="schema",
                    summary="implement Draft 2020-12 strict schema normalizer stripping nullable anyOf unions",
                    deliverables=["uni_lms_mcp/schema_guard.py", "tests/test_schema_guard.py"],
                ),
                CommitMilestone(
                    milestone_id="lms-m2",
                    commit_type="feat",
                    scope="attendance",
                    summary="add multi-channel weekly attendance code aggregator across Ed threads and Moodle forums",
                    deliverables=["uni_lms_mcp/attendance_aggregator.py", "tests/test_attendance.py"],
                ),
                CommitMilestone(
                    milestone_id="lms-m3",
                    commit_type="feat",
                    scope="deadline",
                    summary="add timezone-aware deadline converter and short-extension eligibility evaluator",
                    deliverables=["uni_lms_mcp/deadline_guard.py", "README.md"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="perishable-quota-router",
            pillar="ai-infra-harness",
            tagline="Rolling-window (5h/7d) LLM capacity arbitrage router with 4-stage velocity throttling & cache affinity.",
            origin_context=(
                "Grounded in the 2026-10-16 'Perishable Capacity Arbitrage' insight and production battles on "
                "Personal AI Gateway: 5h/7d dual-window quota tracking, 0-3 velocity pacing, session-sticky prompt caching, and BrokenPipe usage recovery."
            ),
            scheduled_days=["2026-10-27 (Day 3)", "2026-10-28 (Day 4)"],
            tech_stack=["Python", "AsyncIO", "SQLite", "PyTest"],
            milestones=[
                CommitMilestone(
                    milestone_id="pqr-m1",
                    commit_type="feat",
                    scope="router",
                    summary="implement 5h/7d dual-window quota scorer with session-sticky prompt-cache affinity",
                    deliverables=["quota_router/scheduler.py", "tests/test_scheduler.py"],
                ),
                CommitMilestone(
                    milestone_id="pqr-m2",
                    commit_type="feat",
                    scope="throttle",
                    summary="add 4-stage progressive velocity pacing (55%/65%/78% thresholds) and account circuit breaker",
                    deliverables=["quota_router/velocity.py", "tests/test_velocity.py"],
                ),
                CommitMilestone(
                    milestone_id="pqr-m3",
                    commit_type="fix",
                    scope="telemetry",
                    summary="recover upstream token usage on client BrokenPipe disconnect and normalize Protobuf3 zero-values",
                    deliverables=["quota_router/telemetry.py", "tests/test_telemetry.py", "README.md"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="harness-sync-and-purge",
            pillar="ai-infra-harness",
            tagline="Cross-client AI Agent Harness rule synchronizer and dual-anchor cognitive dehydration middleware.",
            origin_context=(
                "Derived from maintaining a single source of truth across 5 coding agents (Cursor, Antigravity, "
                "Claude Code, Codex, Pi) and building the pi-purge dual-anchor anti-preach engine."
            ),
            scheduled_days=["2026-10-29 (Day 5)"],
            tech_stack=["Python", "TypeScript", "CLI", "PyTest"],
            milestones=[
                CommitMilestone(
                    milestone_id="hsp-m1",
                    commit_type="feat",
                    scope="sync",
                    summary="build deterministic rule and skill compiler across Cursor, Antigravity, Claude, Codex, and Pi",
                    deliverables=["harness_sync/compiler.py", "tests/test_compiler.py"],
                ),
                CommitMilestone(
                    milestone_id="hsp-m2",
                    commit_type="feat",
                    scope="purge",
                    summary="implement head/tail dual-anchor prompt injector and wrapper-tag sanitizer",
                    deliverables=["harness_sync/purge_engine.py", "tests/test_purge_engine.py", "README.md"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="evm-funding-arb-sentinel",
            pillar="quant-fintech-web3",
            tagline="EVM delta-neutral vault contracts and perpetual futures funding-rate microstructure backtester.",
            origin_context=(
                "Combines Haodong's interest in compliant institutional digital assets / blockchain smart contracts "
                "(2026-09-17 diary) with practical 4h BTC perpetuals grid and microstructure execution experience."
            ),
            scheduled_days=["2026-10-30 (Day 6)", "2026-10-31 (Day 7)"],
            tech_stack=["Solidity", "Python", "PyTest"],
            milestones=[
                CommitMilestone(
                    milestone_id="efa-m1",
                    commit_type="feat",
                    scope="contracts",
                    summary="implement Solidity delta-neutral basis vault with drawdown circuit breaker and epoch accounting",
                    deliverables=["contracts/DeltaNeutralVault.sol", "tests/test_vault_accounting.py"],
                ),
                CommitMilestone(
                    milestone_id="efa-m2",
                    commit_type="feat",
                    scope="microstructure",
                    summary="add perpetuals funding-rate regime detector and maker/taker basis carry backtester",
                    deliverables=["sentinel/funding_backtest.py", "tests/test_funding_backtest.py", "README.md"],
                ),
            ],
        ),
    ]


class WeeklyPlanner:
    def __init__(self, state_dir: str = "/Users/huanghaodong/Desktop/project/.state"):
        self.state_dir = state_dir
        self.backlog_file = os.path.join(self.state_dir, "backlog.json")

    def load_or_init_projects(self) -> List[PlannedProject]:
        os.makedirs(self.state_dir, exist_ok=True)
        if os.path.exists(self.backlog_file):
            try:
                with open(self.backlog_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                projects: List[PlannedProject] = []
                for item in raw.get("projects", []):
                    milestones = [CommitMilestone(**m) for m in item.get("milestones", [])]
                    item_copy = dict(item)
                    item_copy["milestones"] = milestones
                    projects.append(PlannedProject(**item_copy))
                if projects:
                    return projects
            except Exception:
                pass

        projects = build_default_weekly_projects()
        self.save_projects(projects)
        return projects

    def save_projects(self, projects: List[PlannedProject]) -> None:
        os.makedirs(self.state_dir, exist_ok=True)
        payload = {"projects": [p.to_dict() for p in projects]}
        tmp = self.backlog_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.backlog_file)

    def ingest_signals(self, signals: List[EngineeringSignal]) -> Dict[str, int]:
        """Attach newly discovered conversation/diary signals to matching flagship projects."""
        projects = self.load_or_init_projects()
        pillar_to_project: Dict[str, PlannedProject] = {}
        for p in projects:
            pillar_to_project.setdefault(p.pillar, p)

        added_counts: Dict[str, int] = {p.repo_name: 0 for p in projects}
        for sig in signals:
            target = pillar_to_project.get(sig.pillar, projects[0])
            # More specific routing for LMS/mail signals
            if any(k in (sig.title + sig.summary).lower() for k in ("moodle", "edstem", "mail", "fit10")):
                for p in projects:
                    if p.repo_name == "uni-lms-mcp-suite":
                        target = p
                        break
            elif any(k in (sig.title + sig.summary).lower() for k in ("purge", "harness", "pi-purge")):
                for p in projects:
                    if p.repo_name == "harness-sync-and-purge":
                        target = p
                        break
            elif any(k in (sig.title + sig.summary).lower() for k in ("gateway", "quota", "claude_a", "brokenpipe")):
                for p in projects:
                    if p.repo_name == "perishable-quota-router":
                        target = p
                        break

            existing_ids = {d.get("signal_id") for d in target.dynamic_signals}
            if sig.signal_id not in existing_ids and len(target.dynamic_signals) < 15:
                target.dynamic_signals.append(
                    {
                        "signal_id": sig.signal_id,
                        "date": sig.date,
                        "source_type": sig.source_type,
                        "title": sig.title,
                    }
                )
                added_counts[target.repo_name] += 1

        self.save_projects(projects)
        return added_counts

    def next_actionable_milestone(self, repo_name: Optional[str] = None) -> Optional[ Dict ]:
        """Return the next pending milestone across the weekly plan (or for a specific repo)."""
        projects = self.load_or_init_projects()
        for proj in projects:
            if repo_name and proj.repo_name != repo_name:
                continue
            for ms in proj.milestones:
                if ms.status == "pending":
                    return {"project": proj, "milestone": ms}
        return None

    def mark_milestone_completed(self, milestone_id: str, timestamp_iso: str) -> bool:
        projects = self.load_or_init_projects()
        updated = False
        for proj in projects:
            for ms in proj.milestones:
                if ms.milestone_id == milestone_id:
                    ms.status = "completed"
                    ms.committed_at = timestamp_iso
                    updated = True
        if updated:
            self.save_projects(projects)
        return updated
