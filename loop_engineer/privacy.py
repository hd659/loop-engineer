"""
Zero-Leak Privacy & Secret Redaction Gate.

Ensures that insights extracted from local conversations/diaries and code committed
to public GitHub repositories never leak personal identifiers, credentials, or
private infrastructure endpoints.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class RedactionRule:
    name: str
    pattern: re.Pattern
    replacement: str


DEFAULT_RULES: List[RedactionRule] = [
    RedactionRule(
        name="openai_or_gateway_api_key",
        pattern=re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
        replacement="sk-REDACTED_KEY",
    ),
    RedactionRule(
        name="github_pat",
        pattern=re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        replacement="ghp_REDACTED_TOKEN",
    ),
    RedactionRule(
        name="google_api_key",
        pattern=re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
        replacement="AIzaREDACTED_KEY",
    ),
    RedactionRule(
        name="student_id",
        pattern=re.compile(r"\b37081799\b"),
        replacement="00000000",
    ),
    RedactionRule(
        name="passport_no",
        pattern=re.compile(r"\bEN5074074\b", re.IGNORECASE),
        replacement="REDACTED_ID",
    ),
    RedactionRule(
        name="campus_and_personal_email",
        pattern=re.compile(
            r"\b(?:hhua0127@student\.monash\.edu|huahado@outlook\.com|hufghjuggh@gmail\.com|hadohua6@gmail\.com|s01086538745@gmail\.com|MattiasHassen235@outlook\.com|HuseDependable88@outlook\.com)\b",
            re.IGNORECASE,
        ),
        replacement="builder@example.com",
    ),
    RedactionRule(
        name="phone_numbers",
        pattern=re.compile(r"(?:\+?60\s*1125261626|\b01125261626\b|\+?86\s*15715925855|\+?86\s*15960050929)"),
        replacement="+00-000000000",
    ),
    RedactionRule(
        name="private_handles",
        pattern=re.compile(r"\b(?:WX|TG):[A-Za-z0-9_\u4e00-\u9fa5]{2,32}\b"),
        replacement="USER:REDACTED",
    ),
    RedactionRule(
        name="private_ips_and_hosts",
        pattern=re.compile(
            r"\b(?:101\.230\.211\.50|100\.97\.155\.10|48\.45\.161\.147|50\.114\.32\.105|api\.831800\.xyz|HuangHaodong_5Ghz)\b"
        ),
        replacement="node.example.net",
    ),
]


class PrivacyGate:
    """Scans and sanitizes text or repository files prior to Git commit/push."""

    def __init__(self, rules: List[RedactionRule] = None):
        self.rules = list(rules) if rules is not None else list(DEFAULT_RULES)

    def sanitize_text(self, text: str) -> Tuple[str, List[str]]:
        """Return sanitized text and a list of triggered rule names."""
        if not text:
            return "", []
        triggered: List[str] = []
        out = text
        for rule in self.rules:
            if rule.pattern.search(out):
                triggered.append(rule.name)
                out = rule.pattern.sub(rule.replacement, out)
        return out, triggered

    def scan_text(self, text: str) -> List[str]:
        """Return list of rule names that matched without modifying the text."""
        if not text:
            return []
        return [rule.name for rule in self.rules if rule.pattern.search(text)]

    def assert_clean(self, text: str, context: str = "content") -> None:
        """Raise ValueError if any sensitive pattern is detected in text."""
        hits = self.scan_text(text)
        if hits:
            raise ValueError(f"PrivacyGate blocked {context}: matched sensitive rules {hits}")
