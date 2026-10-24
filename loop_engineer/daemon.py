"""
Autonomous Loop Daemon & On-Demand Model Dispatcher.

Architecture:
- Lightweight Python script stays resident in the background (0 LLM token cost during hourly polling).
- Periodically harvests local conversation & diary signals into `.state/backlog.json`.
- Once per day (or via `python3 loop.py trigger`), the script packages the collected signals and
  next milestone specification into a structured prompt and pushes it to the model via:
  1. Primary: Antigravity Hub (`agentapi new-conversation`) in `/Users/huanghaodong/Desktop/project`
  2. Fallback: Local/VPS Personal AI Gateway (`http://127.0.0.1:18318/v1` / `http://127.0.0.1:8318/v1`)
- The model wakes up, writes the code, runs `pytest`, commits & pushes to `hd659`, and exits immediately.
"""

import json
import os
import re
import subprocess
import time
import urllib.request
from typing import Dict, Optional

from .collector import ConversationCollector
from .github_sync import GitHubSyncManager
from .planner import CommitMilestone, PlannedProject, WeeklyPlanner

AGENTAPI_BIN = "/Users/huanghaodong/.gemini/antigravity/bin/agentapi"


def discover_antigravity_bridge() -> Optional[Dict]:
    """Dynamically discover running Antigravity Hub language_server port and CSRF token."""
    try:
        ps_out = subprocess.check_output(["ps", "-axo", "pid,command"], text=True, timeout=5)
    except Exception:
        return None

    target_pid = None
    csrf_token = None
    for line in ps_out.splitlines():
        if "Antigravity.app/Contents/Resources/bin/language_server" in line and "--csrf_token" in line:
            parts = line.strip().split(None, 1)
            if not parts:
                continue
            target_pid = parts[0]
            m = re.search(r"--csrf_token\s+([A-Za-z0-9_-]+)", line)
            if m:
                csrf_token = m.group(1)
            break

    if not target_pid or not csrf_token:
        return None

    try:
        lsof_out = subprocess.check_output(
            ["/usr/sbin/lsof", "-a", "-nP", "-iTCP", "-sTCP:LISTEN", "-p", str(target_pid)],
            text=True,
            timeout=5,
        )
    except Exception:
        return None

    ports = [int(m.group(1)) for m in re.finditer(r"127\.0\.0\.1:(\d+)\s+\(LISTEN\)", lsof_out)]
    if not ports:
        return None

    chosen_port = ports[-1]
    for p in ports:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{p}/healthz", timeout=1.5) as resp:
                if resp.status == 200:
                    chosen_port = p
                    break
        except Exception:
            pass

    return {
        "pid": int(target_pid),
        "ls_address": f"localhost:{chosen_port}",
        "csrf_token": csrf_token,
    }


class LoopDaemon:
    def __init__(
        self,
        root_dir: str = "/Users/huanghaodong/Desktop/project",
        state_dir: str = "/Users/huanghaodong/Desktop/project/.state",
    ):
        self.root_dir = root_dir
        self.state_dir = state_dir
        self.pid_file = os.path.join(self.state_dir, "daemon.pid")
        self.log_file = os.path.join(self.state_dir, "daemon.log")
        self.status_file = os.path.join(self.state_dir, "daemon_status.json")
        self.dispatch_state_file = os.path.join(self.state_dir, "dispatch_state.json")
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
        return {"last_dispatch_date": "", "dispatched_milestones": {}}

    def _save_dispatch_state(self, state: Dict) -> None:
        os.makedirs(self.state_dir, exist_ok=True)
        tmp = self.dispatch_state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.dispatch_state_file)

    def build_milestone_prompt(self, project: PlannedProject, milestone: CommitMilestone) -> str:
        """Construct the actionable prompt pushed by the script to wake up the model."""
        recent_sigs = project.dynamic_signals[-5:] if project.dynamic_signals else []
        sigs_text = "\n".join(
            f"- [{s.get('date')}] ({s.get('source_type')}) {s.get('title')}" for s in recent_sigs
        ) or "- 无新增对话信号，按周计划既定 Milestone 推进"

        return (
            f"【Loop Engineer 每日自动造物任务（免读写 recent-conversations.md）】\n"
            f"当前目标项目：`{project.repo_name}`（模式：`{project.mode}`，本地目录：`{project.local_target_dir}`）\n"
            f"项目定位：{project.tagline}\n"
            f"背景来源：{project.origin_context}\n"
            f"近期关联对话与日记信号：\n{sigs_text}\n\n"
            f"请立即执行 Milestone `{milestone.milestone_id}`：\n"
            f"1. 在 `{project.local_target_dir}` 下实现交付文件：`{', '.join(milestone.deliverables)}`；\n"
            f"2. 运行 `pytest -q` 确保全部测试 100% 通过，并通过 `PrivacyGate` 隐私检查；\n"
            f"3. 使用 `GitHubSyncManager` 提交 Commit：`{milestone.commit_type}({milestone.scope}): {milestone.summary}`；\n"
            f"4. 调用 `WeeklyPlanner().mark_milestone_completed('{milestone.milestone_id}', ...)` 标记完成，并推送至 `https://github.com/hd659/{project.repo_name}`；\n"
            f"5. 完成后直接结束本轮对话（切勿启动任何定时器）。"
        )

    def dispatch_next_milestone_to_model(self, force: bool = False) -> Dict:
        """Push the next actionable milestone to Antigravity (`agentapi`) to wake up the model on demand."""
        today = time.strftime("%Y-%m-%d")
        dstate = self._load_dispatch_state()
        if not force and dstate.get("last_dispatch_date") == today:
            return {"dispatched": False, "reason": f"Already dispatched a build today ({today})."}

        next_item = self.planner.next_actionable_milestone()
        if not next_item:
            return {"dispatched": False, "reason": "All planned milestones completed."}

        proj: PlannedProject = next_item["project"]
        ms: CommitMilestone = next_item["milestone"]
        title = f"[LoopBuild {today}] {proj.repo_name} · {ms.milestone_id}"
        prompt = self.build_milestone_prompt(proj, ms)

        bridge = discover_antigravity_bridge()
        if not bridge or not os.path.exists(AGENTAPI_BIN):
            self.log(f"Antigravity bridge unavailable; queued prompt for {ms.milestone_id}")
            return {"dispatched": False, "reason": "Antigravity language_server not running."}

        env = dict(os.environ)
        env.pop("ANTIGRAVITY_SOURCE_METADATA", None)
        env.pop("ANTIGRAVITY_CONVERSATION_ID", None)
        env.pop("ANTIGRAVITY_TRAJECTORY_ID", None)
        env["ANTIGRAVITY_LS_ADDRESS"] = bridge["ls_address"]
        env["ANTIGRAVITY_CSRF_TOKEN"] = bridge["csrf_token"]

        cmd = [AGENTAPI_BIN, "new-conversation", "--title", title, "--", prompt]
        out = subprocess.check_output(cmd, env=env, cwd=self.root_dir, text=True, timeout=20)
        resp = json.loads(out) if out.strip() else {}
        conv_id = (
            ((resp.get("response") or {}).get("newConversation") or {}).get("conversationId")
            or resp.get("conversationId")
            or ""
        )
        dstate["last_dispatch_date"] = today
        dstate["dispatched_milestones"][ms.milestone_id] = {
            "conversation_id": conv_id,
            "date": today,
            "title": title,
        }
        self._save_dispatch_state(dstate)
        self.log(f"Dispatched {ms.milestone_id} ({proj.repo_name}) to model conversation {conv_id}")
        return {"dispatched": True, "conversation_id": conv_id, "milestone_id": ms.milestone_id, "title": title}

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
            # Trigger daily model build once per new calendar day (after 11:00 AM local time)
            current_hour = int(time.strftime("%H"))
            if current_hour >= 11:
                try:
                    dispatch_res = self.dispatch_next_milestone_to_model(force=False)
                except Exception as exc:
                    dispatch_res = {"dispatched": False, "error": str(exc)}

        status_payload = {
            "last_poll_ts": int(time.time()),
            "last_poll_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
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

        # Record today (2026-10-25) as already dispatched since Day 1 (`loop-engineer`) is already pushed!
        dstate = self._load_dispatch_state()
        if not dstate.get("last_dispatch_date"):
            dstate["last_dispatch_date"] = time.strftime("%Y-%m-%d")
            self._save_dispatch_state(dstate)

        self.log(f"Started loop-engineer daemon (PID={os.getpid()}, interval={interval_seconds}s)")
        while True:
            try:
                self.run_poll_and_sync_cycle(auto_dispatch=True)
            except Exception as exc:
                self.log(f"Cycle error: {exc}")
            time.sleep(max(60, int(interval_seconds)))
