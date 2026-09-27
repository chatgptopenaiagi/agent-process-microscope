"""Best-effort defense in depth; never a guarantee that arbitrary text is safe."""
from __future__ import annotations

import re
from collections.abc import Mapping

REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(r"(?i)(?:password|passwd|pwd|secret|token|api[_-]?key|authorization|cookie|credential|private[_-]?key)")
_ASSIGNMENT = re.compile(r'''(?ix)(\b[\w.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|credential)[\w.-]*\s*[=:]\s*)(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\s&;,]+)''')
_FLAG = re.compile(r'''(?ix)(--?[\w-]*(?:password|passwd|secret|token|api[-_]?key|credential)[\w-]*\s+)(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\s]+)''')
_AUTH = re.compile(r"(?i)(\b(?:authorization\s*[:=]\s*(?:bearer\s+|basic\s+)?|bearer\s+))[^\s,;\"']+")
_COOKIE = re.compile(r"(?im)(\b(?:set-cookie|cookie)\s*:\s*)[^\r\n]+")
_KEY = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,}|AKIA[A-Z0-9]{16}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b")
_PRIVATE = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|\Z)", re.S)
_URL_AUTH = re.compile(r"(https?://)[^\s/@:]+:[^\s/@]+@", re.I)
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]|\x1b\[[0-?]*[ -/]*[@-~]")
_FORBIDDEN = {"reasoning", "reasoningcontent", "chainofthought", "analysis", "environment", "env", "cookies", "filecontent", "prompt", "stdout", "stderr", "aggregatedoutput"}


def redact_text(value: str, limit: int = 8192) -> str:
    # Redact before truncating so a cut does not expose the beginning of a secret.
    value = _PRIVATE.sub(REDACTED, str(value))
    value = _COOKIE.sub(lambda m: m[1] + REDACTED, value)
    value = _AUTH.sub(lambda m: m[1] + REDACTED, value)
    value = _ASSIGNMENT.sub(lambda m: m[1] + REDACTED, value)
    value = _FLAG.sub(lambda m: m[1] + REDACTED, value)
    value = _KEY.sub(REDACTED, value)
    value = _URL_AUTH.sub(r"\1[REDACTED]@", value)
    value = _CONTROL.sub("", value)
    return value[:limit] + ("…[TRUNCATED]" if len(value) > limit else "")


def sanitize(value, depth: int = 0):
    if depth > 8:
        return "[DEPTH LIMIT]"
    if isinstance(value, Mapping):
        result = {}
        for key, item in list(value.items())[:100]:
            key = str(key)
            if re.sub(r'[^a-z0-9]', '', key.lower()) in _FORBIDDEN:
                result[redact_text(key, 120)] = "[NOT COLLECTED]"
            else:
                result[redact_text(key, 120)] = REDACTED if _SECRET_KEY.search(key) else sanitize(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        result = []
        hide_next = False
        for item in value[:200]:
            if hide_next:
                result.append(REDACTED)
                hide_next = False
            else:
                result.append(sanitize(item, depth + 1))
                hide_next = isinstance(item, str) and item.startswith('-') and bool(_SECRET_KEY.search(item)) and '=' not in item
        return result
    if isinstance(value, str):
        return redact_text(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return redact_text(str(value))
