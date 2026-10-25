"""
Autonomous Loop Daemon & Pi Agent (`claude-opus-5-5-high`) Dispatcher.

Architecture:
- Lightweight Python script stays resident in the background (0 LLM token cost during polling).
- Harvests local conversation & diary signals into `.state/backlog.json`.
- When triggered (either on daily schedule or immediately via `loop.py trigger` / `loop.py run-plan`),
  the script packages the milestone specification and dispatches it to **Pi Agent (`pi`)**
  using **`local-gateway/claude-opus-5-5-high`** (Opus 5.5 via local gateway `:18318`).
- Pi wakes up, writes the code and unit tests, runs `pytest`, commits & pushes to `hd659`, and exits.
"""

import json
import os
import re
import subprocess
import time
from typing import Dict, List, Optional

from .collector import ConversationCollector, EngineeringSignal
from .github_sync import GitHubSyncManager
from .planner import CommitMilestone, PlannedProject, WeeklyPlanner

PI_BIN = "/Users/huanghaodong/.npm-global/bin/pi"
DEFAULT_PI_MODEL = "local-gateway/claude-opus-5-5-high"
DEFAULT_DAILY_QUOTA = 3


class LoopDaemon:
    def __init__(
        self,
        root_dir: str = "/Users/huanghaodong/Desktop/project",
        state_dir: str = "/Users/huanghaodong/Desktop/project/.state",
        pi_model: str = DEFAULT_PI_MODEL,
        daily_quota: int = DEFAULT_DAILY_QUOTA,
    ):
        self.root_dir = root_dir
        self.state_dir = state_dir
        self.pi_model = pi_model
        self.daily_quota = max(1, int(daily_quota))
        self.pid_file = os.path.join(self.state_dir, "daemon.pid")
        self.runner_pid_file = os.path.join(self.state_dir, "runner.pid")
        self.log_file = os.path.join(self.state_dir, "daemon.log")
        self.status_file = os.path.join(self.state_dir, "daemon_status.json")
        self.dispatch_state_file = os.path.join(self.state_dir, "dispatch_state.json")
        self.pi_runs_dir = os.path.join(self.state_dir, "pi_runs")
        self.collector = ConversationCollector()
        self.planner = WeeklyPlanner(state_dir=self.state_dir)
        self.git_sync = GitHubSyncManager(root_dir=self.root_dir, state_dir=self.state_dir)

    def log(self, message: str) -> None:
        os.makedirs(self.state_dir, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)

    def _load_dispatch_state(self) -> Dict:
        if os.path.exists(self.dispatch_state_file):
            try:
                with open(self.dispatch_state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "daily_dispatch_counts" not in data:
                    data["daily_dispatch_counts"] = {}
                return data
            except Exception:
                pass
        return {
            "engine": "pi",
            "model": self.pi_model,
            "last_dispatch_date": "",
            "daily_dispatch_counts": {},
            "active_milestone": None,
            "dispatched_milestones": {},
        }

    def synthesize_milestones_via_pi(self, signals: List[EngineeringSignal]) -> List[str]:
        """
        When the backlog runs out of pending milestones, invoke Pi (`claude-opus-5-5-high`)
        to synthesize 2 new projects/milestones directly from the user's latest conversations and diaries.
        """
        projects = self.planner.load_or_init_projects()
        existing_repos = [
            f"- {p.repo_name} ({p.mode}): {[m.milestone_id for m in p.milestones]}"
            for p in projects
        ]
        recent_sigs = [
            f"- [{s.date}] ({s.pillar} / {s.source_type}) {s.title}: {s.summary[:160]}"
            for s in signals[:15]
        ]
        synth_prompt = (
            "【Loop Engineer 动态需求合成器 · 只输出纯 JSON，不要调用任何写文件工具】\n"
            "请分析以下最新的本地对话与思考日记信号，结合已有仓库列表，提炼生成 1~2 个高价值的新项目（`extrapolate_new`）或已有项目的新演进阶段（`self_optimize`），每个包含 2 个可由 pytest 验证的 Milestone。\n\n"
            "已有仓库与 Milestone：\n" + "\n".join(existing_repos) + "\n\n"
            "最新对话与日记信号：\n" + "\n".join(recent_sigs) + "\n\n"
            "请严格只输出一个 ```json ... ``` 代码块，格式为数组：\n"
            "```json\n"
            "[\n"
            "  {\n"
            '    "repo_name": "kebab-case-slug",\n'
            '    "pillar": "ai-infra-harness | workflow-mcp | quant-fintech-web3 | cognitive-systems",\n'
            '    "mode": "extrapolate_new",\n'
            '    "local_target_dir": "/Users/huanghaodong/Desktop/project/workspaces/kebab-case-slug",\n'
            '    "tagline": "[New Extrapolated Project] Concise cold engineering description.",\n'
            '    "origin_context": "Why this was synthesized from the recent conversation signals.",\n'
            '    "tech_stack": ["Python", "PyTest"],\n'
            '    "milestones": [\n'
            "      {\n"
            '        "milestone_id": "unique-id-m1",\n'
            '        "commit_type": "feat",\n'
            '        "scope": "core",\n'
            '        "summary": "concise commit summary",\n'
            '        "deliverables": ["pkg/module.py", "tests/test_module.py"]\n'
            "      }\n"
            "    ]\n"
            "  }\n"
            "]\n"
            "```"
        )
        env = dict(os.environ)
        env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:/Users/huanghaodong/.npm-global/bin:/opt/anaconda3/bin:{env.get('PATH', '')}"
        cmd = [
            PI_BIN,
            "--print",
            "--model",
            self.pi_model,
            "--thinking",
            "low",
            "--no-mcp",
            "--no-tools",
            "--",
            synth_prompt,
        ]
        try:
            self.log(f"Synthesizing new milestones from {len(signals)} conversation signals via Pi ({self.pi_model})...")
            proc = subprocess.run(cmd, cwd=self.root_dir, env=env, capture_output=True, text=True, timeout=300)
            out = proc.stdout or ""
            match = re.search(r"```json\s*(\[.*?\])\s*```", out, re.DOTALL)
            raw_json = match.group(1) if match else out.strip()
            items = json.loads(raw_json)
            if isinstance(items, list):
                added = self.planner.merge_llm_synthesized_plan(items)
                self.log(f"Synthesized {len(added)} new milestones via Pi: {added}")
                return added
        except Exception as exc:
            self.log(f"Pi synthesis skipped/failed ({exc}); relying on deterministic synthesizer.")
        return []

    def _save_dispatch_state(self, state: Dict) -> None:
        os.makedirs(self.state_dir, exist_ok=True)
        tmp = self.dispatch_state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.dispatch_state_file)

    def build_milestone_prompt(self, project: PlannedProject, milestone: CommitMilestone) -> str:
        """Construct the self-contained prompt pushed by the script to wake up Pi (`claude-opus-5-5-high`)."""
        recent_sigs = project.dynamic_signals[-5:] if project.dynamic_signals else []
        sigs_text = "\n".join(
            f"- [{s.get('date')}] ({s.get('source_type')}) {s.get('title')}" for s in recent_sigs
        ) or "- 按周计划既定 Milestone 推进"

        # For `self_optimize` projects like `netmap` that may contain private domain strings locally,
        # instruct Pi to also sync a sanitized public copy or replace hardcoded private domain with env var.
        privacy_note = (
            "注意：如果目标目录已有文件中含私人网关域名或私人 IP，请将其改为 `os.environ.get('GATEWAY_PUBLIC_HOST', 'api.example.com')` 以通过 `PrivacyGate` 零泄漏检查（严禁将私人域名或 IP 推上公开 GitHub）。"
            if project.mode == "self_optimize"
            else "注意：所有代码与文档严禁包含任何私人邮箱、学号、真实 API Key 或私人域名（必须 100% 通过 `PrivacyGate` 检查）。"
        )

        return (
            f"【Loop Engineer 自动造物任务 · 免读写 recent-conversations.md 与 Obsidian 知识库】\n"
            f"当前目标仓库：`{project.repo_name}`\n"
            f"引擎模式：`{project.mode}`\n"
            f"本地目标目录：`{project.local_target_dir}`\n"
            f"项目定位：{project.tagline}\n"
            f"背景与痛点推导：{project.origin_context}\n"
            f"技术栈：{', '.join(project.tech_stack)}\n"
            f"关联对话信号：\n{sigs_text}\n\n"
            f"{privacy_note}\n"
            f"【防截断硬约束（必读）】网关单次响应上限为 `max_tokens=20480`。请保持每个源码/测试文件精炼高内聚（严格控制在 `100~200` 行以内），**每轮只调用 1 次 `write` 工具写 1 个文件**，分多轮依次写完 `{', '.join(milestone.deliverables)}`，严禁在单轮中一次性输出超长代码导致 `stopReason=length` 截断！\n\n"
            f"请立即完成 Milestone `{milestone.milestone_id}`：\n"
            f"1. 确保目录 `{project.local_target_dir}` 存在，分步编写高质量、真实可运行的交付文件：`{', '.join(milestone.deliverables)}`（若已有相关文件则在其基础上演进升级，保持代码精炼硬核）；\n"
            f"2. 在 `{project.local_target_dir}` 下运行 `/opt/anaconda3/bin/python3 -m pytest -q` 验证全部单元测试 100% 通过；\n"
            f"3. 在 `/Users/huanghaodong/Desktop/project` 下调用 Python 执行提交与推送：\n"
            f"```python\n"
            f"import time, sys\n"
            f"sys.path.insert(0, '/Users/huanghaodong/Desktop/project')\n"
            f"from loop_engineer.github_sync import GitHubSyncManager\n"
            f"from loop_engineer.planner import WeeklyPlanner\n"
            f"sync = GitHubSyncManager()\n"
            f"sync.ensure_git_repo('{project.local_target_dir}')\n"
            f"# 若目录内有未跟踪的核心源码也可一并加入\n"
            f"ok, rev = sync.commit_files('{project.local_target_dir}', {milestone.deliverables!r}, '{milestone.commit_type}({milestone.scope}): {milestone.summary}')\n"
            f"ok_push, msg = sync.push_or_create_remote('{project.local_target_dir}', '{project.repo_name}', {project.tagline!r})\n"
            f"WeeklyPlanner().mark_milestone_completed('{milestone.milestone_id}', time.strftime('%Y-%m-%dT%H:%M:%S%z'))\n"
            f"print('COMMIT:', ok, rev, 'PUSH:', ok_push, msg)\n"
            f"```\n"
            f"4. 执行完成后直接输出简短总结并结束，不要询问用户。"
        )

    def dispatch_next_milestone_to_model(self, force: bool = False, repo_name: Optional[str] = None) -> Dict:
        """Invoke Pi Agent (`pi --print --model local-gateway/claude-opus-5-5-high`) to execute the next milestone."""
        today = time.strftime("%Y-%m-%d")
        dstate = self._load_dispatch_state()
        daily_counts = dstate.get("daily_dispatch_counts") or {}
        today_count = int(daily_counts.get(today, 0))
        if not force and today_count >= self.daily_quota:
            return {
                "dispatched": False,
                "reason": f"Daily quota reached ({today_count}/{self.daily_quota}) for {today}. Use --force to run now.",
            }

        next_item = self.planner.next_actionable_milestone(repo_name=repo_name)
        if not next_item:
            signals = self.collector.collect_all()
            self.synthesize_milestones_via_pi(signals)
            next_item = self.planner.next_actionable_milestone(repo_name=repo_name)
        if not next_item:
            return {"dispatched": False, "reason": "All planned milestones completed."}

        proj: PlannedProject = next_item["project"]
        ms: CommitMilestone = next_item["milestone"]
        os.makedirs(proj.local_target_dir, exist_ok=True)
        os.makedirs(self.pi_runs_dir, exist_ok=True)

        title = f"[LoopBuild {today}] {proj.repo_name} · {ms.milestone_id}"
        prompt = self.build_milestone_prompt(proj, ms)
        run_log_path = os.path.join(self.pi_runs_dir, f"{ms.milestone_id}.log")

        env = dict(os.environ)
        env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:/Users/huanghaodong/.npm-global/bin:/opt/anaconda3/bin:{env.get('PATH', '')}"

        project_session_dir = "/Users/huanghaodong/.pi/agent/sessions/--Users-huanghaodong-Desktop-project--"
        os.makedirs(project_session_dir, exist_ok=True)

        cmd = [
            PI_BIN,
            "--print",
            "--model",
            self.pi_model,
            "--thinking",
            "low",
            "--no-mcp",
            "--session-dir",
            project_session_dir,
            "--name",
            title,
            "--",
            prompt,
        ]

        dstate["active_milestone"] = {
            "milestone_id": ms.milestone_id,
            "repo_name": proj.repo_name,
            "model": self.pi_model,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "log_file": run_log_path,
        }
        self._save_dispatch_state(dstate)
        self.log(f"Launching Pi ({self.pi_model}) for {proj.repo_name} :: {ms.milestone_id} -> {run_log_path}")

        with open(run_log_path, "w", encoding="utf-8") as log_f:
            log_f.write(f"=== {title} | model={self.pi_model} ===\n\n")
            log_f.flush()
            proc = subprocess.run(
                cmd,
                cwd=proj.local_target_dir,
                env=env,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1200,
            )

        # Check whether milestone was actually completed
        after_next = self.planner.next_actionable_milestone(repo_name=proj.repo_name)
        completed_ok = proc.returncode == 0 and (
            not after_next or after_next["milestone"].milestone_id != ms.milestone_id
        )

        dstate = self._load_dispatch_state()
        if "daily_dispatch_counts" not in dstate or not isinstance(dstate["daily_dispatch_counts"], dict):
            dstate["daily_dispatch_counts"] = {}
        if completed_ok:
            dstate["last_dispatch_date"] = today
            dstate["daily_dispatch_counts"][today] = int(dstate["daily_dispatch_counts"].get(today, 0)) + 1
        dstate["active_milestone"] = None
        dstate["dispatched_milestones"][ms.milestone_id] = {
            "repo_name": proj.repo_name,
            "model": self.pi_model,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "exit_code": proc.returncode,
            "completed": completed_ok,
            "log_file": run_log_path,
        }
        self._save_dispatch_state(dstate)
        self.log(
            f"Finished Pi ({self.pi_model}) for {ms.milestone_id} "
            f"(exit_code={proc.returncode}, completed={completed_ok}, "
            f"today_quota={dstate['daily_dispatch_counts'].get(today, 0)}/{self.daily_quota})"
        )
        return {
            "dispatched": True,
            "engine": "pi",
            "model": self.pi_model,
            "repo_name": proj.repo_name,
            "milestone_id": ms.milestone_id,
            "exit_code": proc.returncode,
            "completed": completed_ok,
            "today_dispatched": dstate["daily_dispatch_counts"].get(today, 0),
            "daily_quota": self.daily_quota,
            "log_file": run_log_path,
        }

    def run_all_pending_milestones(self, max_count: int = 20) -> List[Dict]:
        """Sequentially execute all pending milestones across the weekly plan using Pi (`claude-opus-5-5-high`)."""
        results: List[Dict] = []
        retry_counts: Dict[str, int] = {}
        for _ in range(max_count):
            nxt = self.planner.next_actionable_milestone()
            if not nxt:
                break
            ms_id = nxt["milestone"].milestone_id
            res = self.dispatch_next_milestone_to_model(force=True)
            results.append(res)
            # Safety guard: allow up to 2 attempts per milestone in case of transient 429 or length truncation
            after = self.planner.next_actionable_milestone()
            if after and after["milestone"].milestone_id == ms_id:
                retry_counts[ms_id] = retry_counts.get(ms_id, 0) + 1
                if retry_counts[ms_id] >= 2:
                    self.log(f"Milestone {ms_id} remained pending after 2 Pi runs; stopping sequential runner for inspection.")
                    break
                self.log(f"Milestone {ms_id} still pending after attempt 1; sleeping 5s and retrying once...")
                time.sleep(5)
        return results

    def start_plan_runner_detached(self, max_count: int = 20) -> int:
        """Fork a background runner that executes pending milestones via Pi (`claude-opus-5-5-high`)."""
        os.makedirs(self.state_dir, exist_ok=True)
        if os.path.exists(self.runner_pid_file):
            try:
                old_pid = int(open(self.runner_pid_file, "r", encoding="utf-8").read().strip())
                os.kill(old_pid, 0)
                return old_pid
            except Exception:
                pass

        pid1 = os.fork()
        if pid1 > 0:
            time.sleep(0.3)
            try:
                return int(open(self.runner_pid_file, "r", encoding="utf-8").read().strip())
            except Exception:
                return pid1

        os.setsid()
        pid2 = os.fork()
        if pid2 > 0:
            os._exit(0)

        devnull_fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull_fd, 0)
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        if devnull_fd > 2:
            os.close(devnull_fd)

        with open(self.runner_pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        self.log(f"Started Pi (`{self.pi_model}`) batch plan runner (PID={os.getpid()}, max_count={max_count})")
        try:
            self.run_all_pending_milestones(max_count=max_count)
        except Exception as exc:
            self.log(f"Batch runner error: {exc}")
        finally:
            try:
                os.remove(self.runner_pid_file)
            except OSError:
                pass
        os._exit(0)

    def run_poll_and_sync_cycle(self, auto_dispatch: bool = False) -> Dict:
        """Execute one silent collection + backlog enrichment pass (0 LLM tokens unless synthesis or auto_dispatch triggers)."""
        os.makedirs(self.state_dir, exist_ok=True)
        signals = self.collector.collect_all()
        ingested = self.planner.ingest_signals(signals)
        next_item = self.planner.next_actionable_milestone()
        if not next_item and signals:
            self.synthesize_milestones_via_pi(signals)
            next_item = self.planner.next_actionable_milestone()

        next_summary = None
        if next_item:
            proj = next_item["project"]
            ms = next_item["milestone"]
            next_summary = {
                "repo_name": proj.repo_name,
                "mode": proj.mode,
                "milestone_id": ms.milestone_id,
                "commit_header": f"{ms.commit_type}({ms.scope}): {ms.summary}",
                "deliverables": ms.deliverables,
            }

        dispatch_res = None
        if auto_dispatch:
            try:
                dispatch_res = self.dispatch_next_milestone_to_model(force=False)
                # Refresh next_item after dispatch so status_payload reflects post-dispatch queue
                next_item = self.planner.next_actionable_milestone()
                if next_item:
                    proj = next_item["project"]
                    ms = next_item["milestone"]
                    next_summary = {
                        "repo_name": proj.repo_name,
                        "mode": proj.mode,
                        "milestone_id": ms.milestone_id,
                        "commit_header": f"{ms.commit_type}({ms.scope}): {ms.summary}",
                        "deliverables": ms.deliverables,
                    }
                else:
                    next_summary = None
            except Exception as exc:
                dispatch_res = {"dispatched": False, "error": str(exc)}

        status_payload = {
            "last_poll_ts": int(time.time()),
            "last_poll_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "engine": "pi",
            "pi_model": self.pi_model,
            "daily_quota": self.daily_quota,
            "total_signals_collected": len(signals),
            "newly_ingested_by_repo": ingested,
            "next_actionable_milestone": next_summary,
            "last_dispatch": dispatch_res or self._load_dispatch_state(),
            "github_account": self.git_sync.load_account_config(),
        }
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(status_payload, f, ensure_ascii=False, indent=2)

        self.log(
            f"Polled {len(signals)} signals; ingested={sum(ingested.values())}; "
            f"next={next_summary['milestone_id'] if next_summary else 'NONE'}"
        )
        return status_payload

    def start_detached(self, interval_seconds: int = 3600) -> int:
        """Start the lightweight Python polling daemon as a detached background process."""
        os.makedirs(self.state_dir, exist_ok=True)
        if os.path.exists(self.pid_file):
            try:
                old_pid = int(open(self.pid_file, "r", encoding="utf-8").read().strip())
                os.kill(old_pid, 0)
                return old_pid
            except Exception:
                pass

        pid1 = os.fork()
        if pid1 > 0:
            time.sleep(0.3)
            try:
                return int(open(self.pid_file, "r", encoding="utf-8").read().strip())
            except Exception:
                return pid1

        os.setsid()
        pid2 = os.fork()
        if pid2 > 0:
            os._exit(0)

        devnull_fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull_fd, 0)
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        if devnull_fd > 2:
            os.close(devnull_fd)

        with open(self.pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        self.log(f"Started loop-engineer daemon (PID={os.getpid()}, engine=pi, model={self.pi_model}, interval={interval_seconds}s)")
        while True:
            try:
                self.run_poll_and_sync_cycle(auto_dispatch=True)
            except Exception as exc:
                self.log(f"Cycle error: {exc}")
            time.sleep(max(60, int(interval_seconds)))
