"""
Multi-Source Conversation & Thought Collector.

Silently polls Haodong's local knowledge base and agent transcripts:
1. Obsidian Recent Conversations (`08-topics/recent-conversations.md`)
2. Thought Diaries (`~/Documents/diary/*.md`)
3. Obsidian Active Project Playbooks (`01-projects/_active/*.md`)
4. Antigravity Conversation Transcripts (`~/.gemini/antigravity/brain/*/.system_generated/logs/transcript.jsonl`)

Extracts structured engineering signals, passes them through `PrivacyGate`, and classifies
them into the 4 `BuilderPersona` pillars.
"""

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from .persona import BuilderPersona, DEFAULT_PERSONA
from .privacy import PrivacyGate


@dataclass
class EngineeringSignal:
    signal_id: str
    date: str
    source_type: str  # "recent_conversation" | "thought_diary" | "project_playbook" | "transcript"
    title: str
    summary: str
    pillar: str
    source_path: str
    redacted_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


class ConversationCollector:
    def __init__(
        self,
        recent_conv_path: str = "/Users/huanghaodong/Documents/Obsidian Vault/08-topics/recent-conversations.md",
        archive_conv_path: str = "/Users/huanghaodong/Documents/Obsidian Vault/08-topics/recent-conversations-archive.md",
        diary_dir: str = "/Users/huanghaodong/Documents/diary",
        active_projects_dir: str = "/Users/huanghaodong/Documents/Obsidian Vault/01-projects/_active",
        agy_brain_dir: str = "/Users/huanghaodong/.gemini/antigravity/brain",
        pi_sessions_dir: str = "/Users/huanghaodong/.pi/agent/sessions",
        persona: BuilderPersona = DEFAULT_PERSONA,
        privacy_gate: Optional[PrivacyGate] = None,
    ):
        self.recent_conv_path = recent_conv_path
        self.archive_conv_path = archive_conv_path
        self.diary_dir = diary_dir
        self.active_projects_dir = active_projects_dir
        self.agy_brain_dir = agy_brain_dir
        self.pi_sessions_dir = pi_sessions_dir
        self.persona = persona
        self.privacy_gate = privacy_gate or PrivacyGate()

    @staticmethod
    def _make_id(prefix: str, key: str) -> str:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        return f"{prefix}-{digest}"

    @staticmethod
    def _is_meta_loop_check(text: str) -> bool:
        lowered = (text or "").lower()
        ignore_phrases = (
            "询问当前是否在做项目",
            "你现在在做项目吗",
            "为什么今天没有做任务",
            "loop engineer 自动造物任务",
            "[loopbuild ",
            "诊断 `loop-engineer` 今日未自动执行",
        )
        return any(p in lowered for p in ignore_phrases)

    def _parse_conversation_markdown(self, md_path: str, limit: int = 30) -> List[EngineeringSignal]:
        if not os.path.exists(md_path):
            return []
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        pattern = re.compile(
            r"^###\s+(\d{4}-\d{2}-\d{2})\s+·\s+([^\n]+)\n"
            r"(?:-\s+状态：[^\n]*\n)?"
            r"(?:-\s+Agent：[^\n]*\n)?"
            r"-\s+摘要：([^\n]+)",
            re.MULTILINE,
        )
        signals: List[EngineeringSignal] = []
        for match in pattern.finditer(content):
            if len(signals) >= limit:
                break
            date_str = match.group(1).strip()
            raw_title = match.group(2).strip()
            raw_summary = re.sub(r"\s+", " ", match.group(3).strip())
            if self._is_meta_loop_check(f"{raw_title} {raw_summary}"):
                continue

            clean_title, hits1 = self.privacy_gate.sanitize_text(raw_title)
            clean_summary, hits2 = self.privacy_gate.sanitize_text(raw_summary)
            combined_hits = sorted(set(hits1 + hits2))
            pillar = self.persona.classify_topic(f"{clean_title} {clean_summary}")
            sig_id = self._make_id("conv", f"{date_str}:{raw_title}")
            signals.append(
                EngineeringSignal(
                    signal_id=sig_id,
                    date=date_str,
                    source_type="recent_conversation",
                    title=clean_title,
                    summary=clean_summary,
                    pillar=pillar,
                    source_path=md_path,
                    redacted_rules=combined_hits,
                )
            )
        return signals

    def collect_recent_conversations(self) -> List[EngineeringSignal]:
        """Parse `recent-conversations.md` and recent entries of `recent-conversations-archive.md`."""
        active = self._parse_conversation_markdown(self.recent_conv_path, limit=25)
        archived = self._parse_conversation_markdown(self.archive_conv_path, limit=20)
        return active + archived

    def collect_thought_diaries(self) -> List[EngineeringSignal]:
        """Parse cognitive models and commercial/quant insights from `~/Documents/diary/`."""
        if not os.path.isdir(self.diary_dir):
            return []
        signals: List[EngineeringSignal] = []
        for fname in sorted(os.listdir(self.diary_dir), reverse=True):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(self.diary_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue

            date_match = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", fname)
            date_str = date_match.group(1) if date_match else "2026-10-01"
            heading_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            raw_title = heading_match.group(1).strip() if heading_match else fname
            body_preview = re.sub(r"\s+", " ", text[:600]).strip()

            clean_title, hits1 = self.privacy_gate.sanitize_text(raw_title)
            clean_summary, hits2 = self.privacy_gate.sanitize_text(body_preview)
            pillar = self.persona.classify_topic(f"{clean_title} {clean_summary}")
            sig_id = self._make_id("diary", fname)
            signals.append(
                EngineeringSignal(
                    signal_id=sig_id,
                    date=date_str,
                    source_type="thought_diary",
                    title=clean_title,
                    summary=clean_summary[:320],
                    pillar=pillar,
                    source_path=fpath,
                    redacted_rules=sorted(set(hits1 + hits2)),
                )
            )
        return signals

    def collect_recent_transcripts(self, max_conversations: int = 8) -> List[EngineeringSignal]:
        """Scan recent Antigravity `transcript.jsonl` files for user requests."""
        if not os.path.isdir(self.agy_brain_dir):
            return []
        candidates = []
        for conv_id in os.listdir(self.agy_brain_dir):
            tpath = os.path.join(
                self.agy_brain_dir, conv_id, ".system_generated", "logs", "transcript.jsonl"
            )
            if os.path.isfile(tpath):
                try:
                    candidates.append((os.path.getmtime(tpath), conv_id, tpath))
                except OSError:
                    pass
        candidates.sort(reverse=True)
        signals: List[EngineeringSignal] = []

        for _, conv_id, tpath in candidates[:max_conversations]:
            try:
                with open(tpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        obj = json.loads(line)
                        if obj.get("type") == "USER_INPUT":
                            raw_content = str(obj.get("content") or "")
                            req_match = re.search(
                                r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_content, re.DOTALL
                            )
                            user_text = (
                                req_match.group(1).strip() if req_match else raw_content.strip()
                            )
                            user_text = re.sub(r"\s+", " ", user_text)
                            if len(user_text) < 15 or self._is_meta_loop_check(user_text):
                                continue
                            created_at = str(obj.get("created_at") or "2026-10-25")[:10]
                            clean_text, hits = self.privacy_gate.sanitize_text(user_text)
                            pillar = self.persona.classify_topic(clean_text)
                            sig_id = self._make_id("agy", f"{conv_id}:{obj.get('step_index', 0)}")
                            signals.append(
                                EngineeringSignal(
                                    signal_id=sig_id,
                                    date=created_at,
                                    source_type="transcript",
                                    title=clean_text[:72],
                                    summary=clean_text[:280],
                                    pillar=pillar,
                                    source_path=tpath,
                                    redacted_rules=hits,
                                )
                            )
                            break
            except Exception:
                continue
        return signals

    def collect_pi_sessions(self, max_sessions: int = 10) -> List[EngineeringSignal]:
        """Scan recent Pi Client JSONL sessions for organic user prompts (skipping automated LoopBuild sessions)."""
        if not os.path.isdir(self.pi_sessions_dir):
            return []
        candidates = []
        for root, _, files in os.walk(self.pi_sessions_dir):
            for fname in files:
                if fname.endswith(".jsonl"):
                    fpath = os.path.join(root, fname)
                    try:
                        candidates.append((os.path.getmtime(fpath), fname, fpath))
                    except OSError:
                        pass
        candidates.sort(reverse=True)
        signals: List[EngineeringSignal] = []

        for _, fname, fpath in candidates[: max_sessions * 2]:
            if len(signals) >= max_sessions:
                break
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        obj = json.loads(line)
                        if obj.get("type") == "session_info" and "[LoopBuild" in str(obj.get("name", "")):
                            break
                        if obj.get("type") == "message":
                            msg = obj.get("message") or {}
                            if msg.get("role") == "user":
                                parts = msg.get("content") or []
                                text_chunks = [
                                    str(p.get("text", ""))
                                    for p in parts
                                    if isinstance(p, dict) and p.get("type") == "text"
                                ]
                                user_text = re.sub(r"\s+", " ", " ".join(text_chunks).strip())
                                if len(user_text) < 15 or self._is_meta_loop_check(user_text):
                                    break
                                ts_str = str(obj.get("timestamp") or fname[:10])[:10]
                                clean_text, hits = self.privacy_gate.sanitize_text(user_text)
                                pillar = self.persona.classify_topic(clean_text)
                                sig_id = self._make_id("pi", fname)
                                signals.append(
                                    EngineeringSignal(
                                        signal_id=sig_id,
                                        date=ts_str,
                                        source_type="pi_session",
                                        title=clean_text[:72],
                                        summary=clean_text[:280],
                                        pillar=pillar,
                                        source_path=fpath,
                                        redacted_rules=hits,
                                    )
                                )
                                break
            except Exception:
                continue
        return signals

    def collect_all(self) -> List[EngineeringSignal]:
        """Collect and deduplicate signals across all local sources."""
        all_signals = (
            self.collect_recent_conversations()
            + self.collect_thought_diaries()
            + self.collect_recent_transcripts()
            + self.collect_pi_sessions()
        )
        seen = set()
        unique: List[EngineeringSignal] = []
        for sig in all_signals:
            if sig.signal_id not in seen:
                seen.add(sig.signal_id)
                unique.append(sig)
        return unique
