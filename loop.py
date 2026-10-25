#!/usr/bin/env python3
"""
CLI entrypoint for `loop-engineer`.

Commands:
  python3 loop.py status                  # Inspect daemon status, active Pi run, and next milestone
  python3 loop.py poll                    # Run a conversation/diary collection pass and update backlog
  python3 loop.py plan                    # Print the 7-day dual-engine project schedule and milestones
  python3 loop.py trigger --force         # Immediately run the next milestone via Pi (`claude-opus-5-5-high`)
  python3 loop.py run-plan --detach       # Immediately execute all planned milestones sequentially via Pi (`claude-opus-5-5-high`)
  python3 loop.py daemon --detach         # Start the background hourly polling daemon
  python3 loop.py bind-github ...         # Bind a GitHub account, rewrite commit author, and push all repos
"""

import argparse
import json
import os
import subprocess
import sys

from loop_engineer.daemon import DEFAULT_DAILY_QUOTA, DEFAULT_PI_MODEL, LoopDaemon
from loop_engineer.github_sync import GH_BIN, GitHubSyncManager
from loop_engineer.planner import WeeklyPlanner


def _check_pid(pid_file: str):
    if os.path.exists(pid_file):
        try:
            pid = int(open(pid_file, "r", encoding="utf-8").read().strip())
            os.kill(pid, 0)
            return pid
        except Exception:
            return None
    return None


def cmd_status(args):
    daemon = LoopDaemon(pi_model=getattr(args, "model", DEFAULT_PI_MODEL))
    state = daemon.run_poll_and_sync_cycle()
    state["daemon_pid"] = _check_pid(daemon.pid_file)
    state["plan_runner_pid"] = _check_pid(daemon.runner_pid_file)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_plan(args):
    planner = WeeklyPlanner()
    projects = planner.load_or_init_projects()
    for idx, proj in enumerate(projects, 1):
        done = sum(1 for m in proj.milestones if m.status == "completed")
        total = len(proj.milestones)
        print(f"[{idx}] {proj.repo_name} ({proj.mode} | {proj.pillar}) — {done}/{total} milestones completed")
        print(f"    Target: {proj.local_target_dir}")
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

    sync.rewrite_author_history(sync.root_dir, username, email)
    print("Normalized commit author history on `loop-engineer`.")

    if args.push:
        ok, msg = sync.push_or_create_remote(
            sync.root_dir,
            "loop-engineer",
            description="Conversation-driven autonomous GitHub incubator & existing-project self-optimizer.",
        )
        print(f"[loop-engineer] push={ok}: {msg}")


def cmd_daemon(args):
    daemon = LoopDaemon(pi_model=args.model, daily_quota=args.daily_quota)
    if args.detach:
        pid = daemon.start_detached(interval_seconds=args.interval)
        print(
            f"Loop daemon running in background (PID={pid}, model={args.model}, "
            f"daily_quota={args.daily_quota}, interval={args.interval}s)."
        )
    else:
        daemon.run_poll_and_sync_cycle(auto_dispatch=True)


def cmd_synthesize(args):
    daemon = LoopDaemon(pi_model=args.model)
    signals = daemon.collector.collect_all()
    det_added = daemon.planner.auto_synthesize_from_signals(signals)
    llm_added = daemon.synthesize_milestones_via_pi(signals) if args.llm else []
    print(
        json.dumps(
            {
                "signals_scanned": len(signals),
                "deterministic_milestones_added": det_added,
                "llm_milestones_added": llm_added,
                "next_actionable": daemon.planner.next_actionable_milestone() is not None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_trigger(args):
    daemon = LoopDaemon(pi_model=args.model)
    daemon.run_poll_and_sync_cycle(auto_dispatch=False)
    res = daemon.dispatch_next_milestone_to_model(force=args.force, repo_name=args.repo)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_run_plan(args):
    daemon = LoopDaemon(pi_model=args.model)
    daemon.run_poll_and_sync_cycle(auto_dispatch=False)
    if args.detach:
        pid = daemon.start_plan_runner_detached(max_count=args.max_count)
        print(f"Started Pi ({args.model}) sequential plan runner in background (PID={pid}).")
    else:
        res = daemon.run_all_pending_milestones(max_count=args.max_count)
        print(json.dumps(res, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="loop-engineer CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Poll sources and display current loop status")
    sub.add_parser("poll", help="Run a collection and backlog ingestion pass")
    sub.add_parser("plan", help="Display the 7-day flagship project schedule")

    p_trig = sub.add_parser("trigger", help="Immediately dispatch the next milestone to Pi (Opus 5.5)")
    p_trig.add_argument("--force", action="store_true", help="Dispatch even if today already ran")
    p_trig.add_argument("--repo", default="", help="Optional specific repo_name to target")
    p_trig.add_argument("--model", default=DEFAULT_PI_MODEL, help="Pi model identifier")

    p_run = sub.add_parser("run-plan", help="Execute all pending milestones in the plan via Pi (Opus 5.5)")
    p_run.add_argument("--max-count", type=int, default=20, help="Maximum milestones to execute sequentially")
    p_run.add_argument("--model", default=DEFAULT_PI_MODEL, help="Pi model identifier")
    p_run.add_argument("--detach", action="store_true", help="Run sequentially in background")

    p_bind = sub.add_parser("bind-github", help="Bind a GitHub account and push repositories")
    p_bind.add_argument("--username", default="", help="GitHub username")
    p_bind.add_argument("--email", default="", help="Git author email for contribution graph")
    p_bind.add_argument("--visibility", choices=["public", "private"], default="public")
    p_bind.add_argument("--login-web", action="store_true", help="Run interactive `gh auth login -w` first")
    p_bind.add_argument("--push", action="store_true", default=True, help="Create remote repos and push immediately")

    p_daemon = sub.add_parser("daemon", help="Start or run the background loop daemon")
    p_daemon.add_argument("--interval", type=int, default=3600, help="Polling interval in seconds")
    p_daemon.add_argument("--daily-quota", type=int, default=DEFAULT_DAILY_QUOTA, help="Max milestones to auto-dispatch per day")
    p_daemon.add_argument("--model", default=DEFAULT_PI_MODEL, help="Pi model identifier")
    p_daemon.add_argument("--detach", action="store_true", help="Detach daemon into background")

    p_synth = sub.add_parser("synthesize", help="Synthesize new projects/milestones from latest conversations")
    p_synth.add_argument("--llm", action="store_true", help="Also invoke Pi (Opus 5.5) for dynamic synthesis")
    p_synth.add_argument("--model", default=DEFAULT_PI_MODEL, help="Pi model identifier")

    args = parser.parse_args()
    if args.cmd in ("status", "poll", None):
        cmd_status(args)
    elif args.cmd == "plan":
        cmd_plan(args)
    elif args.cmd == "bind-github":
        cmd_bind_github(args)
    elif args.cmd == "daemon":
        cmd_daemon(args)
    elif args.cmd == "synthesize":
        cmd_synthesize(args)
    elif args.cmd == "trigger":
        cmd_trigger(args)
    elif args.cmd == "run-plan":
        cmd_run_plan(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
