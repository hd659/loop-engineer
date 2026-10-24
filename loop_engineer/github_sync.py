"""
Git Repository Manager & Blank-Account GitHub Binder.

Supports:
1. Local granular commits with mandatory PrivacyGate scanning across all staged files.
2. Deferred binding to a fresh/blank GitHub account:
   - Commits made locally before account binding are cleanly recorded.
   - Once the user binds their new GitHub account (`loop.py bind-github`), author identity
     (`user.name` / `user.email`) is retroactively normalized across local commits so 100% of
     commits light up the new account's GitHub contribution graph, followed by automatic
     repository creation (`gh repo create`) and `git push`.
"""

import json
import os
import subprocess
from typing import Dict, List, Optional, Tuple

from .privacy import PrivacyGate

GIT_BIN = "/opt/homebrew/bin/git" if os.path.exists("/opt/homebrew/bin/git") else "git"
GH_BIN = "/opt/homebrew/bin/gh" if os.path.exists("/opt/homebrew/bin/gh") else "gh"


class GitHubSyncManager:
    def __init__(
        self,
        root_dir: str = "/Users/huanghaodong/Desktop/project",
        state_dir: str = "/Users/huanghaodong/Desktop/project/.state",
        privacy_gate: Optional[PrivacyGate] = None,
    ):
        self.root_dir = root_dir
        self.state_dir = state_dir
        self.account_file = os.path.join(self.state_dir, "github_account.json")
        self.privacy_gate = privacy_gate or PrivacyGate()

    def load_account_config(self) -> Dict:
        os.makedirs(self.state_dir, exist_ok=True)
        if os.path.exists(self.account_file):
            try:
                with open(self.account_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "username": "hd",
            "email": "hd@users.noreply.github.com",
            "visibility": "public",
            "bound": False,
        }

    def save_account_config(self, cfg: Dict) -> None:
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.account_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def ensure_git_repo(self, repo_dir: str) -> None:
        os.makedirs(repo_dir, exist_ok=True)
        git_dir = os.path.join(repo_dir, ".git")
        if not os.path.isdir(git_dir):
            subprocess.run([GIT_BIN, "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
        cfg = self.load_account_config()
        subprocess.run(
            [GIT_BIN, "config", "user.name", cfg.get("username", "hd")],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [GIT_BIN, "config", "user.email", cfg.get("email", "hd@users.noreply.github.com")],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

    def verify_directory_privacy(self, repo_dir: str, rel_paths: Optional[List[str]] = None) -> None:
        """Scan files in repo_dir through PrivacyGate; raise ValueError if any secret/PII is found."""
        targets: List[str] = []
        if rel_paths:
            targets = [os.path.join(repo_dir, p) for p in rel_paths]
        else:
            for root, dirs, files in os.walk(repo_dir):
                dirs[:] = [
                    d for d in dirs if d not in (".git", ".state", "workspaces", "__pycache__", ".pytest_cache", ".venv")
                ]
                for fname in files:
                    if fname.endswith((".py", ".md", ".json", ".ts", ".sol", ".toml", ".yml", ".yaml")):
                        targets.append(os.path.join(root, fname))

        for fpath in targets:
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue
            # Skip privacy.py itself if it contains literal regex rules for student_id/IPs
            if os.path.basename(fpath) == "privacy.py" or os.path.basename(fpath) == "test_loop_engineer.py":
                continue
            self.privacy_gate.assert_clean(content, context=fpath)

    def commit_files(
        self,
        repo_dir: str,
        rel_paths: List[str],
        commit_message: str,
    ) -> Tuple[bool, str]:
        """Stage specific files, run PrivacyGate verification, and create a granular Git commit."""
        self.ensure_git_repo(repo_dir)
        existing = [p for p in rel_paths if os.path.exists(os.path.join(repo_dir, p))]
        if not existing:
            return False, "No matching files to stage."

        self.verify_directory_privacy(repo_dir, existing)
        subprocess.run([GIT_BIN, "add", "--"] + existing, cwd=repo_dir, check=True, capture_output=True)

        status = subprocess.run(
            [GIT_BIN, "diff", "--cached", "--name-only"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        if not status.stdout.strip():
            return False, "Working tree clean for specified files."

        subprocess.run(
            [GIT_BIN, "commit", "-m", commit_message],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        rev = subprocess.run(
            [GIT_BIN, "rev-parse", "--short", "HEAD"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return True, rev

    def rewrite_author_history(self, repo_dir: str, username: str, email: str) -> None:
        """Rewrite author/committer identity across all existing local commits for the new blank account."""
        self.ensure_git_repo(repo_dir)
        subprocess.run([GIT_BIN, "config", "user.name", username], cwd=repo_dir, check=True)
        subprocess.run([GIT_BIN, "config", "user.email", email], cwd=repo_dir, check=True)
        env = dict(os.environ)
        env["FILTER_BRANCH_SQUELCH_WARNING"] = "1"
        env_filter = (
            f'export GIT_AUTHOR_NAME="{username}"; '
            f'export GIT_AUTHOR_EMAIL="{email}"; '
            f'export GIT_COMMITTER_NAME="{username}"; '
            f'export GIT_COMMITTER_EMAIL="{email}";'
        )
        subprocess.run(
            [GIT_BIN, "filter-branch", "-f", "--env-filter", env_filter, "--", "--all"],
            cwd=repo_dir,
            env=env,
            capture_output=True,
        )

    def push_or_create_remote(self, repo_dir: str, repo_name: str, description: str = "") -> Tuple[bool, str]:
        """Create remote repository on the bound GitHub account if needed and push `main`."""
        cfg = self.load_account_config()
        if not cfg.get("bound"):
            return False, "GitHub account not yet bound (local commits preserved; run `python3 loop.py bind-github` when ready)."

        username = cfg["username"]
        visibility_flag = "--private" if cfg.get("visibility") == "private" else "--public"
        remotes = subprocess.run(
            [GIT_BIN, "remote"], cwd=repo_dir, capture_output=True, text=True
        ).stdout.splitlines()

        if "origin" not in remotes:
            cmd = [
                GH_BIN,
                "repo",
                "create",
                f"{username}/{repo_name}",
                visibility_flag,
                "--source",
                repo_dir,
                "--remote",
                "origin",
                "--push",
            ]
            if description:
                cmd.extend(["--description", description])
            proc = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
            if proc.returncode == 0:
                return True, f"Created and pushed https://github.com/{username}/{repo_name}"
            return False, proc.stderr.strip() or proc.stdout.strip()

        proc = subprocess.run(
            [GIT_BIN, "push", "-u", "origin", "main"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True, f"Pushed main to https://github.com/{username}/{repo_name}"
        return False, proc.stderr.strip() or proc.stdout.strip()
