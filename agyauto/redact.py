"""Scrub secrets before anything is stored or shown in the dashboard."""
import re

_PATTERNS = [
    (re.compile(r"\bbot\d{6,}:[A-Za-z0-9_-]{20,}"), "bot<redacted>"),
    (re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_-]{16,}"), r"\1-<redacted>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "gh_<redacted>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "github_pat_<redacted>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AKIA<redacted>"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), "AIza<redacted>"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "xox-<redacted>"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 <redacted>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "<jwt-redacted>"),
    (re.compile(r"(?i)\b([A-Za-z0-9_]*(?:password|passwd|secret|token|api[_-]?key)[A-Za-z0-9_]*\s*[=:]\s*)(['\"]?)[^\s'\"&]{4,}"),
     r"\1\2<redacted>"),
    (re.compile(r"(?i)(://[^/\s:@]+:)[^/\s@]{3,}(@)"), r"\1<redacted>\2"),
]


def redact(text):
    for rx, rep in _PATTERNS:
        text = rx.sub(rep, text)
    return text
