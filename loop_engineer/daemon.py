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
import subprocess
import time
from typing import Dict, List, Optional

from .collector import ConversationCollector
from .github_sync import GitHubSyncManager
from .planner import CommitMilestone, PlannedProject, WeeklyPlanner

PI_BIN = "/Users/huanghaodong/.npm-global/bin/pi"
DEFAULT_PI_MODEL = "local-gateway/claude-opus-5-5-high"


class LoopDaemon:
    def __init__(
        self,
        root_dir: str = "/Users/huanghaodong/Desktop/project",
        state_dir: str = "/Users/huanghaodong/Desktop/project/.state",
        pi_model: str = DEFAULT_PI_MODEL,
    ):
        self.root_dir = root_dir
        self.state_dir = state_dir
        self.pi_model = pi_model
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
                    return json.load(f)
            except Exception:
                pass
        return {
            "engine": "pi",
            "model": self.pi_model,
            "last_dispatch_date": "",
            "active_milestone": None,
            "dispatched_milestones": {},
        }

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
            f"{privacy_note}\n\n"
            f"请立即完成 Milestone `{milestone.milestone_id}`：\n"
            f"1. 确保目录 `{project.local_target_dir}` 存在，编写高质量、真实可运行的交付文件：`{', '.join(milestone.deliverables)}`（若已有相关文件则在其基础上演进升级，保持代码精炼硬核）；\n"
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
        if not force and dstate.get("last_dispatch_date") == today:
            return {"dispatched": False, "reason": f"Already dispatched today ({today}). Use --force to run now."}

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

        dstate = self._load_dispatch_state()
        dstate["last_dispatch_date"] = today
        dstate["active_milestone"] = None
        dstate["dispatched_milestones"][ms.milestone_id] = {
            "repo_name": proj.repo_name,
            "model": self.pi_model,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "exit_code": proc.returncode,
            "log_file": run_log_path,
        }
        self._save_dispatch_state(dstate)
        self.log(f"Finished Pi ({self.pi_model}) for {ms.milestone_id} (exit_code={proc.returncode})")
        return {
            "dispatched": True,
            "engine": "pi",
            "model": self.pi_model,
            "repo_name": proj.repo_name,
            "milestone_id": ms.milestone_id,
            "exit_code": proc.returncode,
            "log_file": run_log_path,
        }

    def run_all_pending_milestones(self, max_count: int = 20) -> List[Dict]:
        """Sequentially execute all pending milestones across the weekly plan using Pi (`claude-opus-5-5-high`)."""
        results: List[Dict] = []
        for _ in range(max_count):
            nxt = self.planner.next_actionable_milestone()
            if not nxt:
                break
            ms_id = nxt["milestone"].milestone_id
            res = self.dispatch_next_milestone_to_model(force=True)
            results.append(res)
            # Safety guard: if Pi exited without marking milestone completed, avoid infinite loop on same milestone
            after = self.planner.next_actionable_milestone()
            if after and after["milestone"].milestone_id == ms_id:
                self.log(f"Milestone {ms_id} remained pending after Pi run; stopping sequential runner for inspection.")
                break
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
        """Execute one silent collection + backlog enrichment pass (0 LLM tokens unless auto_dispatch triggers)."""
        os.makedirs(self.state_dir, exist_ok=True)
        signals = self.collector.collect_all()
        ingested = self.planner.ingest_signals(signals)
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
            current_hour = int(time.strftime("%H"))
            if current_hour >= 11:
                try:
                    dispatch_res = self.dispatch_next_milestone_to_model(force=False)
                except Exception as exc:
                    dispatch_res = {"dispatched": False, "error": str(exc)}

        status_payload = {
            "last_poll_ts": int(time.time()),
            "last_poll_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "engine": "pi",
            "pi_model": self.pi_model,
            "total_signals_collected": len(signals),
            "newly_ingested_by_repo": ingested,
            "next_actionable_milestone": next_summary,
            "last_dispatch": dispatch_res or self._load_dispatch_state(),
            "github_account": self.git_sync.load_account_config(),
        }
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(status_payload, f, ensure_ascii=False, indent=2)

        self.log(
            f"Polled {len(signals)} signals (0 tokens); ingested={sum(ingested.values())}; "
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
