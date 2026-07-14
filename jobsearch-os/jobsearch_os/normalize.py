"""Normalization (Section K): canonical URLs, description hashing, ATS job-id
extraction, and a rule-based requirement extractor. All deterministic."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

DEFAULT_TRACKING_PARAMS = {"gclid", "fbclid", "ref", "src", "mc_cid", "mc_eid"}
TRACKING_PREFIXES = ("utm_",)


def canonical_url(url: str, tracking_params: set[str] | None = None) -> str:
    """Lowercase scheme+host; strip fragment; strip tracking params; normalize
    trailing slash; PRESERVE path segments and non-tracking query params
    (greenhouse/lever/workday job ids live there)."""
    if not url:
        return ""
    tracking = tracking_params if tracking_params is not None else DEFAULT_TRACKING_PARAMS
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    kept = []
    for k, v in parse_qsl(parts.query, keep_blank_values=False):
        kl = k.lower()
        if kl in tracking or any(kl.startswith(p) for p in TRACKING_PREFIXES):
            continue
        kept.append((k, v))
    query = urlencode(sorted(kept))

    return urlunsplit((scheme, netloc, path, query, ""))  # fragment dropped


_GREENHOUSE = re.compile(r"greenhouse\.io/[^/]+/jobs/(\d+)", re.IGNORECASE)
_LEVER = re.compile(r"lever\.co/[^/]+/([0-9a-f\-]{8,})", re.IGNORECASE)
_GH_JID = re.compile(r"[?&]gh_jid=(\d+)")
_WORKDAY = re.compile(r"/job/[^/]+/[^/]*?_(?:JR|R)-?(\d+)", re.IGNORECASE)


def extract_ats_job_id(url: str) -> str | None:
    if not url:
        return None
    for pat, prefix in ((_GREENHOUSE, "gh:"), (_LEVER, "lever:"), (_GH_JID, "gh:"), (_WORKDAY, "wd:")):
        m = pat.search(url)
        if m:
            return prefix + m.group(1)
    return None


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def description_hash(description: str) -> str:
    return hashlib.sha256(_normalize_text(description).encode("utf-8")).hexdigest()


_REQ_CUES = re.compile(
    r"\b(experience|years?|proficien|required|must have|must-have|ability to|"
    r"knowledge of|familiar|degree|bachelor|skills?|responsib|you will|you'll)\b",
    re.IGNORECASE,
)


def extract_requirements(description: str) -> list[str]:
    """Rule-based: pull bullet/line items that read like requirements or
    responsibilities. Returns de-duplicated, trimmed lines."""
    if not description:
        return []
    # Split on newlines and common bullet separators.
    raw_lines = re.split(r"[\n\r]+|(?<=[.;])\s+(?=[A-Z])|•|·|•", description)
    out: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        s = line.strip(" \t-*•·—–")
        if len(s) < 8:
            continue
        if _REQ_CUES.search(s):
            key = _normalize_text(s)[:120]
            if key and key not in seen:
                seen.add(key)
                out.append(s.strip())
    return out
