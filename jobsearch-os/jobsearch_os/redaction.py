"""Redaction utility (Invariant 14). Never let a secret reach a log or a prompt.

Matches common secret shapes and known env-var names and replaces the value
with `***REDACTED***`. Used by logging and by any wrapper that captures the
output of an external CLI.
"""
from __future__ import annotations

import re

# Env-var names whose VALUES must never be printed. We redact by value.
SECRET_ENV_NAMES = [
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CLAUDE_REVIEW_MODEL_KEY",
    "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN", "GH_TOKEN",
]

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),                 # OpenAI-style
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"),             # Anthropic-style
    re.compile(r"gh[posru]_[A-Za-z0-9]{20,}"),             # GitHub tokens
    re.compile(r"AKIA[0-9A-Z]{16}"),                        # AWS access key id
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(password\"?\s*[:=]\s*\"?)[^\s\"]+"),
    re.compile(r"(?i)(token\"?\s*[:=]\s*\"?)[A-Za-z0-9._\-]{12,}"),
]

REDACTED = "***REDACTED***"


def redact(text: str, extra_values: list[str] | None = None) -> str:
    if text is None:
        return text
    out = str(text)
    import os
    for name in SECRET_ENV_NAMES:
        val = os.environ.get(name)
        if val:
            out = out.replace(val, REDACTED)
    for val in extra_values or []:
        if val:
            out = out.replace(val, REDACTED)
    for pat in _PATTERNS:
        if pat.groups:
            out = pat.sub(lambda m: m.group(1) + REDACTED, out)
        else:
            out = pat.sub(REDACTED, out)
    return out
