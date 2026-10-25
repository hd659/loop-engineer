"""
Dual-Engine Backlog & 7-Day Progressive Schedule Engine.

Operates on Two Distinct Engines (avoiding redundant clones of already-built projects):
1. Engine A — `self_optimize` (Direct Self-Optimization on Existing Local Projects):
   Finds friction points in Haodong's daily conversations and directly upgrades his
   existing projects (`Desktop/cs/netmap`, `Desktop/cs/moodle-mcp`, `Desktop/cs/edstem-mcp`).
2. Engine B — `extrapolate_new` (Forward Extrapolation from Cognitive Models & Unmet Needs):
   Synthesizes brand-new projects that Haodong has NOT built yet, inferred from his
   thought diaries (Phantom Overload / Single-Thread Slicing, Transaction-Cost Economics,
   Institutional On-Chain Quant) and recurring workflow bottlenecks (pre-submission numeric verification).
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
    mode: str  # "self_optimize" | "extrapolate_new"
    local_target_dir: str
    tagline: str
    origin_context: str
    scheduled_days: List[str]
    tech_stack: List[str]
    milestones: List[CommitMilestone] = field(default_factory=list)
    dynamic_signals: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


def build_default_weekly_projects() -> List[PlannedProject]:
    """Construct the 7-day dual-engine schedule (Existing Project Optimization + Extrapolated New Projects)."""
    return [
        PlannedProject(
            repo_name="loop-engineer",
            pillar="ai-infra-harness",
            mode="extrapolate_new",
            local_target_dir="/Users/huanghaodong/Desktop/project",
            tagline="Conversation-driven autonomous GitHub incubator & existing-project self-optimizer.",
            origin_context=(
                "Built to continuously analyze daily human-agent interactions and thought diaries, "
                "automatically evolving existing local tools and extrapolating brand-new projects."
            ),
            scheduled_days=["2026-10-25 (Day 1)"],
            tech_stack=["Python", "PyTest", "GitHub CLI", "AgentAPI"],
            milestones=[
                CommitMilestone(
                    milestone_id="le-m1",
                    commit_type="feat",
                    scope="core",
                    summary="implement persona filter, zero-leak privacy gate, and multi-source collector",
                    deliverables=["loop_engineer/persona.py", "loop_engineer/privacy.py", "loop_engineer/collector.py"],
                    status="completed",
                ),
                CommitMilestone(
                    milestone_id="le-m2",
                    commit_type="feat",
                    scope="scheduler",
                    summary="add dual-engine 7-day planner (self-optimize + extrapolate-new) and autonomous daemon",
                    deliverables=["loop_engineer/planner.py", "loop_engineer/github_sync.py", "loop_engineer/daemon.py", "loop.py"],
                    status="completed",
                ),
                CommitMilestone(
                    milestone_id="le-m3",
                    commit_type="test",
                    scope="suite",
                    summary="add unit tests for privacy redaction, signal classification, and milestone state machine",
                    deliverables=["tests/test_loop_engineer.py", "README.md", "WEEKLY_PLAN.md"],
                    status="completed",
                ),
            ],
        ),
        PlannedProject(
            repo_name="netmap",
            pillar="workflow-mcp",
            mode="self_optimize",
            local_target_dir="/Users/huanghaodong/Desktop/cs/netmap",
            tagline="[Existing Project Optimization] Upgrade netmap from static proxy viewer to active Split-Tunnel & CDN TTFB Doctor.",
            origin_context=(
                "Directly optimizes `Desktop/cs/netmap` based on the 2026-10-24 Wi-Fi & Misty proxy debugging session: "
                "netmap previously only showed static proxy hops (`ip-api.com`), lacking active detection when a return-to-China "
                "node (`Misty`) hijacks overseas traffic (YouTube/Claude) or suffers evening congestion."
            ),
            scheduled_days=["2026-10-26 (Day 2)"],
            tech_stack=["Python", "HTML/JS", "macOS scutil/lsof"],
            milestones=[
                CommitMilestone(
                    milestone_id="nm-m1",
                    commit_type="feat",
                    scope="probe",
                    summary="add concurrent TTFB latency probes across direct interface, system proxy, and SSH tunnel",
                    deliverables=["server.py", "tests/test_netmap_probe.py"],
                ),
                CommitMilestone(
                    milestone_id="nm-m2",
                    commit_type="feat",
                    scope="doctor",
                    summary="detect split-tunnel routing misconfigurations (overseas targets routed via CN proxy) and render alerts in UI",
                    deliverables=["server.py", "index.html", "README.md"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="single-thread-lock",
            pillar="cognitive-systems",
            mode="extrapolate_new",
            local_target_dir="/Users/huanghaodong/Desktop/project/workspaces/single-thread-lock",
            tagline="[New Extrapolated Project] Anti-TodoList single-aperture execution lock for networked thinkers.",
            origin_context=(
                "Extrapolated from Haodong's 2026-10-09 diary ('Phantom Overload & Activation Friction') and 2026-09-15 diary "
                "('Embodied State Anchoring & Ground-State Reset'), plus why he abandoned Life OS: traditional todo lists expose "
                "50 future tasks at once, triggering RAM overload. This tool hides the backlog completely and exposes ONLY ONE "
                "10-minute physical micro-slice at a time after a 60-second ground-state reset."
            ),
            scheduled_days=["2026-10-27 (Day 3)", "2026-10-28 (Day 4)"],
            tech_stack=["Python", "Textual/CLI", "SQLite", "PyTest"],
            milestones=[
                CommitMilestone(
                    milestone_id="stl-m1",
                    commit_type="feat",
                    scope="vault",
                    summary="implement zero-list brain-dump sink (RAM-to-Disk) and 10-minute micro-slice decomposer",
                    deliverables=["single_thread/vault.py", "tests/test_vault.py"],
                ),
                CommitMilestone(
                    milestone_id="stl-m2",
                    commit_type="feat",
                    scope="aperture",
                    summary="build single-task terminal aperture with ground-state reset timer and anti-peek lock",
                    deliverables=["single_thread/cli.py", "tests/test_aperture.py", "README.md"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="submission-truth-auditor",
            pillar="workflow-mcp",
            mode="extrapolate_new",
            local_target_dir="/Users/huanghaodong/Desktop/project/workspaces/submission-truth-auditor",
            tagline="[New Extrapolated Project] Pre-submission numeric cross-verifier (Shell/Code vs Report PDF) & Viva Question Generator.",
            origin_context=(
                "Extrapolated from Haodong's 2026-10-24 FIT1043 A2 final check (re-running shell pipelines to catch the 127->118 "
                "mismatch in PDF and checking timezone/page limits) and 2026-10-22 FIT1008 D1 live-coding Viva rediscuss prep."
            ),
            scheduled_days=["2026-10-28 (Day 4)", "2026-10-29 (Day 5)"],
            tech_stack=["Python", "AST/Regex", "PyTest"],
            milestones=[
                CommitMilestone(
                    milestone_id="sta-m1",
                    commit_type="feat",
                    scope="auditor",
                    summary="extract numeric claims from Markdown/PDF reports and cross-verify against deterministic script outputs",
                    deliverables=["truth_auditor/numeric_diff.py", "tests/test_numeric_diff.py"],
                ),
                CommitMilestone(
                    milestone_id="sta-m2",
                    commit_type="feat",
                    scope="viva",
                    summary="analyze C++/Python AST complexity invariants to generate adversarial Tutor Viva/Rediscuss questions",
                    deliverables=["truth_auditor/viva_challenger.py", "tests/test_viva.py", "README.md"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="moodle-ed-autopilot-patch",
            pillar="workflow-mcp",
            mode="self_optimize",
            local_target_dir="/Users/huanghaodong/Desktop/cs/moodle-mcp",
            tagline="[Existing Project Optimization] Add MYT timezone deadline normalizer & Short-Extension guard directly to moodle-mcp.",
            origin_context=(
                "Directly optimizes `Desktop/cs/moodle-mcp` based on the 2026-10-23 FIT1043 deadline discovery (Moodle displayed "
                "11:55 PM AEDT which is actually 8:55 PM MYT) and the 2026-10-24 MPU re-enrolment status check."
            ),
            scheduled_days=["2026-10-29 (Day 5)"],
            tech_stack=["Python", "FastMCP", "zoneinfo"],
            milestones=[
                CommitMilestone(
                    milestone_id="map-m1",
                    commit_type="feat",
                    scope="deadline-myt",
                    summary="add AEDT-to-MYT deadline normalizer and Short-Extension window calculator to moodle-mcp",
                    deliverables=["deadline_myt.py", "tests/test_deadline_myt.py"],
                ),
            ],
        ),
        PlannedProject(
            repo_name="dex-cex-friction-radar",
            pillar="quant-fintech-web3",
            mode="extrapolate_new",
            local_target_dir="/Users/huanghaodong/Desktop/project/workspaces/dex-cex-friction-radar",
            tagline="[New Extrapolated Project] On-chain DEX vs CEX perpetuals transaction-cost arbitrage radar & Solidity atomic vault.",
            origin_context=(
                "Synthesizes Haodong's 2026-10-16 'Transaction Cost Economics' insight with his 2026-09-17 desire to build "
                "compliant institutional digital-asset / blockchain quant systems beyond simple CEX grid bots."
            ),
            scheduled_days=["2026-10-30 (Day 6)", "2026-10-31 (Day 7)"],
            tech_stack=["Solidity", "Python", "AsyncIO", "PyTest"],
            milestones=[
                CommitMilestone(
                    milestone_id="dcf-m1",
                    commit_type="feat",
                    scope="friction-engine",
                    summary="model net arbitrage spread between Uniswap v3 concentrated liquidity pools and CEX perps after gas/slippage friction",
                    deliverables=["friction_radar/spread_model.py", "tests/test_spread_model.py"],
                ),
                CommitMilestone(
                    milestone_id="dcf-m2",
                    commit_type="feat",
                    scope="contracts",
                    summary="implement Solidity atomic settlement vault with minimum net-profit guard and flash-rebalance hook",
                    deliverables=["contracts/AtomicFrictionVault.sol", "tests/test_vault_guard.py", "README.md"],
                ),
            ],
        ),
    ]


class WeeklyPlanner:
    def __init__(self, state_dir: str = "/Users/huanghaodong/Desktop/project/.state"):
        self.state_dir = state_dir
        self.backlog_file = os.path.join(self.state_dir, "backlog.json")

    def load_or_init_projects(self, force_reset: bool = False) -> List[PlannedProject]:
        os.makedirs(self.state_dir, exist_ok=True)
        if not force_reset and os.path.exists(self.backlog_file):
            try:
                with open(self.backlog_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                projects: List[PlannedProject] = []
                for item in raw.get("projects", []):
                    if "mode" not in item:
                        break
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
        """Route newly discovered conversation/diary signals to either existing-project optimization or extrapolated repos."""
        projects = self.load_or_init_projects()
        by_name = {p.repo_name: p for p in projects}
        added_counts: Dict[str, int] = {p.repo_name: 0 for p in projects}

        for sig in signals:
            blob = f"{sig.title} {sig.summary}".lower()
            if any(k in blob for k in ("wi-fi", "misty", "netmap", "ipv6", "tailscale", "dns", "路由")):
                target = by_name.get("netmap", projects[0])
            elif any(k in blob for k in ("fit1043", "fit1008", "fit1055", "rubric", "pdf", "rediscuss", "核对")):
                target = by_name.get("submission-truth-auditor", projects[0])
            elif any(k in blob for k in ("moodle", "edstem", "short extension", "mpu", "选课")):
                target = by_name.get("moodle-ed-autopilot-patch", projects[0])
            elif any(k in blob for k in ("过载", "启动", "状态", "冥想", "切片", "overload", "friction", "bayes")):
                target = by_name.get("single-thread-lock", projects[0])
            elif any(k in blob for k in ("区块链", "量化", "交易成本", "套利", "grid", "okx", "blockchain", "quant")):
                target = by_name.get("dex-cex-friction-radar", projects[0])
            else:
                target = by_name.get("loop-engineer", projects[0])

            existing_ids = {d.get("signal_id") for d in target.dynamic_signals}
            if sig.signal_id not in existing_ids and len(target.dynamic_signals) < 50:
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
        self.auto_synthesize_from_signals(signals)
        return added_counts

    def auto_synthesize_from_signals(self, signals: List[EngineeringSignal]) -> List[str]:
        """
        Deterministically synthesize new projects and milestones from newly collected conversation signals
        so that daily engineering discussions continuously expand the actionable backlog.
        """
        projects = self.load_or_init_projects()
        by_name = {p.repo_name: p for p in projects}
        all_ms_ids = {m.milestone_id for p in projects for m in p.milestones}
        created_ms: List[str] = []

        combined_text = " ".join(f"{s.title} {s.summary}" for s in signals).lower()

        # 1. OAuth2 IMAP OTP & Stealth Browser Profile Bridge (from 2026-10-25 Mailbox Vault & Browser Launcher)
        if any(k in combined_text for k in ("邮箱保险箱", "oauth", "imap", "adspower", "browser_launcher", "magic link")):
            if "oauth-imap-otp-extractor" not in by_name:
                proj = PlannedProject(
                    repo_name="oauth-imap-otp-extractor",
                    pillar="ai-infra-harness",
                    mode="extrapolate_new",
                    local_target_dir="/Users/huanghaodong/Desktop/project/workspaces/oauth-imap-otp-extractor",
                    tagline="[New Extrapolated Project] Zero-GUI XOAUTH2 IMAP OTP/Magic-Link extractor & isolated SOCKS5 browser profile launcher.",
                    origin_context=(
                        "Synthesized from 2026-10-25 conversations on building a private Mailbox & OAuth2 Token Vault "
                        "(direct Microsoft OAuth2 IMAP 6-digit OTP and Magic Link extraction) and an AdsPower-free "
                        "isolated US residential SOCKS5 Chromium profile launcher."
                    ),
                    scheduled_days=["2026-10-26 (Wave 2)"],
                    tech_stack=["Python", "IMAP4/XOAUTH2", "SOCKS5", "PyTest"],
                    milestones=[
                        CommitMilestone(
                            milestone_id="oie-m1",
                            commit_type="feat",
                            scope="imap-xoauth2",
                            summary="implement XOAUTH2 access-token refresher and deterministic 6-digit OTP & magic-link MIME parser",
                            deliverables=["otp_vault/imap_xoauth2.py", "tests/test_imap_xoauth2.py"],
                        ),
                        CommitMilestone(
                            milestone_id="oie-m2",
                            commit_type="feat",
                            scope="stealth-bridge",
                            summary="build deterministic per-slot SOCKS5 port allocator and timezone/locale isolated Chromium flag builder",
                            deliverables=["otp_vault/stealth_bridge.py", "tests/test_stealth_bridge.py", "README.md"],
                        ),
                    ],
                )
                projects.append(proj)
                by_name[proj.repo_name] = proj
                created_ms.extend(["oie-m1", "oie-m2"])

        # 2. Zero-Latency LLM Content Moderation & Tarpit Router (from 2026-10-25 omni-moderation & Tarpit)
        if any(k in combined_text for k in ("omni-moderation", "omini", "蜜罐", "tarpit", "酒馆", "前置审核")):
            if "llm-edge-tarpit-guard" not in by_name:
                proj = PlannedProject(
                    repo_name="llm-edge-tarpit-guard",
                    pillar="ai-infra-harness",
                    mode="extrapolate_new",
                    local_target_dir="/Users/huanghaodong/Desktop/project/workspaces/llm-edge-tarpit-guard",
                    tagline="[New Extrapolated Project] Zero-latency code-aware LLM moderation filter & 3-strike SSE tarpit router.",
                    origin_context=(
                        "Synthesized from 2026-10-25 conversations on reverse-engineering `omni-moderation-latest` "
                        "edge filtering: stripping Markdown code blocks and tool_result blocks to guarantee 0% false "
                        "positives on coding prompts while routing 3-strike policy violators into a progressive tarpit."
                    ),
                    scheduled_days=["2026-10-26 (Wave 2)", "2026-10-27 (Wave 2)"],
                    tech_stack=["Python", "Regex/AST", "SSE", "PyTest"],
                    milestones=[
                        CommitMilestone(
                            milestone_id="let-m1",
                            commit_type="feat",
                            scope="moderation",
                            summary="implement code-block & tool-result stripper with weighted jailbreak/moderation risk scorer",
                            deliverables=["edge_guard/moderation_filter.py", "tests/test_moderation_filter.py"],
                        ),
                        CommitMilestone(
                            milestone_id="let-m2",
                            commit_type="feat",
                            scope="tarpit",
                            summary="implement 3-strike sliding-window state machine and progressive latency tarpit policy router",
                            deliverables=["edge_guard/tarpit_router.py", "tests/test_tarpit_router.py", "README.md"],
                        ),
                    ],
                )
                projects.append(proj)
                by_name[proj.repo_name] = proj
                created_ms.extend(["let-m1", "let-m2"])

        # 3. Prompt Prefix-Cache Invalidation Doctor & Cost Simulator (from 2026-10-25 Prefix Caching & 1.0x Billing)
        if any(k in combined_text for k in ("prefix caching", "cached_tokens", "缓存命中", "百分比显示", "haiku", "降级")):
            if "prompt-cache-doctor" not in by_name:
                proj = PlannedProject(
                    repo_name="prompt-cache-doctor",
                    pillar="ai-infra-harness",
                    mode="extrapolate_new",
                    local_target_dir="/Users/huanghaodong/Desktop/project/workspaces/prompt-cache-doctor",
                    tagline="[New Extrapolated Project] LLM prompt prefix-cache invalidation detector, payload rewriter & tier-downgrade cost simulator.",
                    origin_context=(
                        "Synthesized from 2026-10-25 root-cause analysis where placing volatile per-turn JSON state "
                        "ahead of a 27K static rulebook truncated OpenAI/Anthropic prefix caching at 3,200 tokens, "
                        "combined with 1.0x vs 0.1x cache_read billing and Opus-to-Haiku tier downgrade economics."
                    ),
                    scheduled_days=["2026-10-27 (Wave 2)", "2026-10-28 (Wave 2)"],
                    tech_stack=["Python", "JSON-Diff", "Tokenizers", "PyTest"],
                    milestones=[
                        CommitMilestone(
                            milestone_id="pcd-m1",
                            commit_type="feat",
                            scope="prefix-diff",
                            summary="detect volatile token mutations across multi-turn LLM payloads and pinpoint prefix-cache break offset",
                            deliverables=["cache_doctor/prefix_analyzer.py", "tests/test_prefix_analyzer.py"],
                        ),
                        CommitMilestone(
                            milestone_id="pcd-m2",
                            commit_type="feat",
                            scope="optimizer",
                            summary="reorder dynamic state blocks behind static system prefixes and compute cache-hit percentage & USD savings",
                            deliverables=["cache_doctor/payload_optimizer.py", "tests/test_payload_optimizer.py", "README.md"],
                        ),
                    ],
                )
                projects.append(proj)
                by_name[proj.repo_name] = proj
                created_ms.extend(["pcd-m1", "pcd-m2"])

        # 4. Evolve `submission-truth-auditor` with Temporal Drift & Treap Invariant Auditor (from 2026-10-25 FIT1008 HD2 & FIT1061 C4)
        if any(k in combined_text for k in ("treap", "hd2", "model card", "偏移", "碳排")):
            if "submission-truth-auditor" in by_name and "sta-m3" not in all_ms_ids:
                by_name["submission-truth-auditor"].milestones.append(
                    CommitMilestone(
                        milestone_id="sta-m3",
                        commit_type="feat",
                        scope="drift-treap",
                        summary="add temporal concept-drift recall degradation auditor, carbon amortization calculator, and Treap invariant verifier",
                        deliverables=["truth_auditor/drift_and_treap.py", "tests/test_drift_and_treap.py"],
                    )
                )
                created_ms.append("sta-m3")

        if created_ms:
            self.save_projects(projects)
        return created_ms

    def merge_llm_synthesized_plan(self, items: List[Dict]) -> List[str]:
        """Merge LLM-synthesized projects or milestones into `backlog.json` without overwriting existing work."""
        projects = self.load_or_init_projects()
        by_name = {p.repo_name: p for p in projects}
        all_ms_ids = {m.milestone_id for p in projects for m in p.milestones}
        added_ms: List[str] = []

        for raw in items:
            repo_name = str(raw.get("repo_name") or "").strip().lower()
            if not repo_name:
                continue
            raw_milestones = raw.get("milestones") or []
            new_ms_objs: List[CommitMilestone] = []
            for m in raw_milestones:
                ms_id = str(m.get("milestone_id") or "").strip()
                if not ms_id or ms_id in all_ms_ids:
                    continue
                deliverables = [str(d) for d in (m.get("deliverables") or []) if d]
                if not deliverables:
                    continue
                new_ms_objs.append(
                    CommitMilestone(
                        milestone_id=ms_id,
                        commit_type=str(m.get("commit_type") or "feat"),
                        scope=str(m.get("scope") or "core"),
                        summary=str(m.get("summary") or "add synthesized module and unit tests"),
                        deliverables=deliverables,
                        status="pending",
                    )
                )
                all_ms_ids.add(ms_id)
                added_ms.append(ms_id)

            if not new_ms_objs:
                continue

            if repo_name in by_name:
                by_name[repo_name].milestones.extend(new_ms_objs)
            else:
                mode = str(raw.get("mode") or "extrapolate_new")
                target_dir = str(
                    raw.get("local_target_dir")
                    or f"/Users/huanghaodong/Desktop/project/workspaces/{repo_name}"
                )
                proj = PlannedProject(
                    repo_name=repo_name,
                    pillar=str(raw.get("pillar") or "ai-infra-harness"),
                    mode=mode,
                    local_target_dir=target_dir,
                    tagline=str(raw.get("tagline") or f"[New Extrapolated Project] {repo_name}"),
                    origin_context=str(raw.get("origin_context") or "Synthesized from recent agent conversations."),
                    scheduled_days=[str(raw.get("scheduled_day") or "Dynamic Queue")],
                    tech_stack=[str(t) for t in (raw.get("tech_stack") or ["Python", "PyTest"])],
                    milestones=new_ms_objs,
                )
                projects.append(proj)
                by_name[repo_name] = proj

        if added_ms:
            self.save_projects(projects)
        return added_ms

    def next_actionable_milestone(self, repo_name: Optional[str] = None) -> Optional[Dict]:
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
