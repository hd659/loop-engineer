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
        diary_dir: str = "/Users/huanghaodong/Documents/diary",
        active_projects_dir: str = "/Users/huanghaodong/Documents/Obsidian Vault/01-projects/_active",
        agy_brain_dir: str = "/Users/huanghaodong/.gemini/antigravity/brain",
        persona: BuilderPersona = DEFAULT_PERSONA,
        privacy_gate: Optional[PrivacyGate] = None,
    ):
        self.recent_conv_path = recent_conv_path
        self.diary_dir = diary_dir
        self.active_projects_dir = active_projects_dir
        self.agy_brain_dir = agy_brain_dir
        self.persona = persona
        self.privacy_gate = privacy_gate or PrivacyGate()

    @staticmethod
    def _make_id(prefix: str, key: str) -> str:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        return f"{prefix}-{digest}"

    def collect_recent_conversations(self) -> List[EngineeringSignal]:
        """Parse `recent-conversations.md` entries into structured signals."""
        if not os.path.exists(self.recent_conv_path):
            return []
        with open(self.recent_conv_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(
            r"^###\s+(\d{4}-\d{2}-\d{2})\s+·\s+(.+?)\n"
            r"(?:-\s+状态：.*\n)?"
            r"(?:-\s+Agent：.*\n)?"
            r"-\s+摘要：(.+?)(?=\n###\s+\d{4}-\d{2}-\d{2}|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        signals: List[EngineeringSignal] = []
        for match in pattern.finditer(content):
            date_str = match.group(1).strip()
            raw_title = match.group(2).strip()
            raw_summary = re.sub(r"\s+", " ", match.group(3).strip())

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
                    source_path=self.recent_conv_path,
                    redacted_rules=combined_hits,
                )
            )
        return signals

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
                            if len(user_text) < 15:
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

    def collect_all(self) -> List[EngineeringSignal]:
        """Collect and deduplicate signals across all local sources."""
        all_signals = (
            self.collect_recent_conversations()
            + self.collect_thought_diaries()
            + self.collect_recent_transcripts()
        )
        seen = set()
        unique: List[EngineeringSignal] = []
        for sig in all_signals:
            if sig.signal_id not in seen:
                seen.add(sig.signal_id)
                unique.append(sig)
        return unique
