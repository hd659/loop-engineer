#!/usr/bin/env python3
"""
CLI entrypoint for `loop-engineer`.

Commands:
  python3 loop.py status                  # Inspect daemon status, collected signals, and next milestone
  python3 loop.py poll                    # Run a conversation/diary collection pass and update backlog
  python3 loop.py plan                    # Print the 7-day flagship repository schedule and milestones
  python3 loop.py daemon --detach         # Start the background loop daemon
  python3 loop.py bind-github ...         # Bind a fresh GitHub account, rewrite commit author, and push all repos
"""

import argparse
import json
import os
import subprocess
import sys

from loop_engineer.daemon import LoopDaemon
from loop_engineer.github_sync import GH_BIN, GitHubSyncManager
from loop_engineer.planner import WeeklyPlanner


def cmd_status(args):
    daemon = LoopDaemon()
    state = daemon.run_poll_and_sync_cycle()
    pid_alive = None
    if os.path.exists(daemon.pid_file):
        try:
            pid = int(open(daemon.pid_file, "r", encoding="utf-8").read().strip())
            os.kill(pid, 0)
            pid_alive = pid
        except Exception:
            pid_alive = None
    state["daemon_pid"] = pid_alive
    print(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_plan(args):
    planner = WeeklyPlanner()
    projects = planner.load_or_init_projects()
    for idx, proj in enumerate(projects, 1):
        done = sum(1 for m in proj.milestones if m.status == "completed")
        total = len(proj.milestones)
        print(f"[{idx}] {proj.repo_name} ({proj.pillar}) — {done}/{total} milestones completed")
        print(f"    Days: {', '.join(proj.scheduled_days)}")
        print(f"    Tagline: {proj.tagline}")
        for m in proj.milestones:
            mark = "DONE" if m.status == "completed" else "TODO"
            print(f"      - [{mark}] {m.milestone_id}: {m.commit_type}({m.scope}): {m.summary}")
        if proj.dynamic_signals:
            print(f"    Linked signals from conversations/diaries: {len(proj.dynamic_signals)}")
        print()


def cmd_bind_github(args):
    sync = GitHubSyncManager()
    if args.login_web:
        subprocess.run([GH_BIN, "auth", "login", "--hostname", "github.com", "-p", "https", "-w"], check=True)

    username = args.username
    email = args.email
    if not username:
        proc = subprocess.run(
            [GH_BIN, "api", "user", "--jq", ".login"], capture_output=True, text=True
        )
        if proc.returncode == 0 and proc.stdout.strip():
            username = proc.stdout.strip()
        else:
            raise SystemExit("Please provide --username <GITHUB_USERNAME> or run with --login-web first.")

    if not email:
        email = f"{username}@users.noreply.github.com"

    cfg = {
        "username": username,
        "email": email,
        "visibility": args.visibility,
        "bound": True,
    }
    sync.save_account_config(cfg)
    print(f"Saved GitHub account config: username={username}, email={email}, visibility={args.visibility}")

    # Rewrite local commit history in root repo (`loop-engineer`) and any workspace sub-repos
    sync.rewrite_author_history(sync.root_dir, username, email)
    print("Normalized commit author history on `loop-engineer`.")

    if args.push:
        ok, msg = sync.push_or_create_remote(
            sync.root_dir,
            "loop-engineer",
            description="Conversation-driven autonomous GitHub incubator & progressive commit engine.",
        )
        print(f"[loop-engineer] push={ok}: {msg}")

        ws_root = os.path.join(sync.root_dir, "workspaces")
        if os.path.isdir(ws_root):
            for name in sorted(os.listdir(ws_root)):
                sub_dir = os.path.join(ws_root, name)
                if os.path.isdir(os.path.join(sub_dir, ".git")):
                    sync.rewrite_author_history(sub_dir, username, email)
                    ok_sub, msg_sub = sync.push_or_create_remote(sub_dir, name)
                    print(f"[{name}] push={ok_sub}: {msg_sub}")


def cmd_daemon(args):
    daemon = LoopDaemon()
    if args.detach:
        pid = daemon.start_detached(interval_seconds=args.interval)
        print(f"Loop daemon running in background (PID={pid}, interval={args.interval}s).")
    else:
        daemon.run_poll_and_sync_cycle()


def main():
    parser = argparse.ArgumentParser(description="loop-engineer CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Poll sources and display current loop status")
    sub.add_parser("poll", help="Run a collection and backlog ingestion pass")
    sub.add_parser("plan", help="Display the 7-day flagship project schedule")

    p_bind = sub.add_parser("bind-github", help="Bind a blank GitHub account and push repositories")
    p_bind.add_argument("--username", default="", help="New GitHub username")
    p_bind.add_argument("--email", default="", help="Git author email for contribution graph")
    p_bind.add_argument("--visibility", choices=["public", "private"], default="public")
    p_bind.add_argument("--login-web", action="store_true", help="Run interactive `gh auth login -w` first")
    p_bind.add_argument("--push", action="store_true", default=True, help="Create remote repos and push immediately")

    p_daemon = sub.add_parser("daemon", help="Start or run the background loop daemon")
    p_daemon.add_argument("--interval", type=int, default=3600, help="Polling interval in seconds")
    p_daemon.add_argument("--detach", action="store_true", help="Detach daemon into background")

    args = parser.parse_args()
    if args.cmd in ("status", "poll", None):
        cmd_status(args)
    elif args.cmd == "plan":
        cmd_plan(args)
    elif args.cmd == "bind-github":
        cmd_bind_github(args)
    elif args.cmd == "daemon":
        cmd_daemon(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
