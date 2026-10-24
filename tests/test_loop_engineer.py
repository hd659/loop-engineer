"""
Unit test suite for `loop-engineer`.
"""

import os
import tempfile

import pytest

from loop_engineer.collector import ConversationCollector, EngineeringSignal
from loop_engineer.github_sync import GitHubSyncManager
from loop_engineer.persona import DEFAULT_PERSONA
from loop_engineer.planner import WeeklyPlanner, build_default_weekly_projects
from loop_engineer.privacy import PrivacyGate


def test_privacy_gate_redacts_secrets_and_pii():
    gate = PrivacyGate()
    raw = (
        "Student 37081799 with email hhua0127@student.monash.edu used key sk-abc1234567890def "
        "on node 101.230.211.50 and WX:test_user_99."
    )
    sanitized, hits = gate.sanitize_text(raw)
    assert "37081799" not in sanitized
    assert "hhua0127@student.monash.edu" not in sanitized
    assert "sk-abc1234567890def" not in sanitized
    assert "101.230.211.50" not in sanitized
    assert "WX:test_user_99" not in sanitized
    assert set(hits) >= {
        "student_id",
        "campus_and_personal_email",
        "openai_or_gateway_api_key",
        "private_ips_and_hosts",
        "private_handles",
    }

    with pytest.raises(ValueError):
        gate.assert_clean(raw, context="unit_test")


def test_persona_topic_classification():
    assert DEFAULT_PERSONA.classify_topic("Moodle and Edstem attendance MCP tool") == "workflow-mcp"
    assert DEFAULT_PERSONA.classify_topic("Claude 5h/7d quota gateway router and BrokenPipe") == "ai-infra-harness"
    assert DEFAULT_PERSONA.classify_topic("Solidity EVM vault and BTC perpetuals funding rate") == "quant-fintech-web3"
    assert DEFAULT_PERSONA.classify_topic("Perishable capacity arbitrage transaction-cost model") == "cognitive-systems"


def test_weekly_planner_ingests_signals_and_tracks_milestones():
    with tempfile.TemporaryDirectory() as tmpdir:
        planner = WeeklyPlanner(state_dir=tmpdir)
        projects = planner.load_or_init_projects()
        assert len(projects) == 6
        modes = {p.mode for p in projects}
        assert modes == {"self_optimize", "extrapolate_new"}

        dummy_signal = EngineeringSignal(
            signal_id="conv-12345",
            date="2026-10-25",
            source_type="recent_conversation",
            title="Troubleshoot Wi-Fi and Misty proxy routing",
            summary="Check IPv6 and split-tunnel routing on home network.",
            pillar="workflow-mcp",
            source_path="/tmp/mock.md",
        )
        counts = planner.ingest_signals([dummy_signal])
        assert counts["netmap"] == 1

        next_item = planner.next_actionable_milestone(repo_name="netmap")
        assert next_item is not None
        ms_id = next_item["milestone"].milestone_id
        assert ms_id == "nm-m1"

        assert planner.mark_milestone_completed(ms_id, "2026-10-25T00:45:00+08:00")
        next_after = planner.next_actionable_milestone(repo_name="netmap")
        assert next_after["milestone"].milestone_id == "nm-m2"


def test_git_sync_commit_and_author_rewrite():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "repo")
        state_dir = os.path.join(tmpdir, "state")
        sync = GitHubSyncManager(root_dir=repo_dir, state_dir=state_dir)
        sync.ensure_git_repo(repo_dir)

        sample_file = os.path.join(repo_dir, "hello.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("x = 42\n")

        committed, rev = sync.commit_files(repo_dir, ["hello.py"], "feat(core): add sample module")
        assert committed is True
        assert len(rev) >= 6

        sync.rewrite_author_history(repo_dir, "new_blank_user", "new_blank_user@users.noreply.github.com")
        cfg = sync.load_account_config()
        assert cfg["bound"] is False
