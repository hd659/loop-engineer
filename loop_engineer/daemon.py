"""
Autonomous Loop Daemon & Multi-Agent Dispatcher.

Runs silently in the background (0 LLM token overhead while polling).
On each daily/scheduled cycle:
1. Runs `ConversationCollector` to harvest new signals from Obsidian, diaries, and transcripts.
2. Updates `WeeklyPlanner` backlog with newly discovered signals.
3. Dispatches the next pending milestone to either:
   - Antigravity Hub (`agentapi`) in `/Users/huanghaodong/Desktop/project`, OR
   - Local/VPS Personal AI Gateway (`http://127.0.0.1:18318/v1` / `http://127.0.0.1:8318/v1`).
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
from .planner import WeeklyPlanner

AGENTAPI_BIN = "/Users/huanghaodong/.gemini/antigravity/bin/agentapi"


def discover_antigravity_bridge() -> Optional[Dict]:
    """Discover running Antigravity language_server port and CSRF token if active."""
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
        self.collector = ConversationCollector()
        self.planner = WeeklyPlanner(state_dir=self.state_dir)
        self.git_sync = GitHubSyncManager(root_dir=self.root_dir, state_dir=self.state_dir)

    def log(self, message: str) -> None:
        os.makedirs(self.state_dir, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)

    def run_poll_and_sync_cycle(self) -> Dict:
        """Execute one silent collection + backlog enrichment pass."""
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
                "milestone_id": ms.milestone_id,
                "commit_header": f"{ms.commit_type}({ms.scope}): {ms.summary}",
                "deliverables": ms.deliverables,
            }

        status_payload = {
            "last_poll_ts": int(time.time()),
            "last_poll_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "total_signals_collected": len(signals),
            "newly_ingested_by_repo": ingested,
            "next_actionable_milestone": next_summary,
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
        """Start the background loop daemon as a detached process."""
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

        self.log(f"Started loop-engineer daemon (PID={os.getpid()}, interval={interval_seconds}s)")
        while True:
            try:
                self.run_poll_and_sync_cycle()
            except Exception as exc:
                self.log(f"Cycle error: {exc}")
            time.sleep(max(60, int(interval_seconds)))
