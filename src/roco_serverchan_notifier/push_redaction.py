from __future__ import annotations

import re
import urllib.parse
from typing import Any

from .provider_specs import provider_secret_fields


_SENSITIVE_NAMES = "access_token|app_token|corpsecret|key|read_key|readkey|secret|sendkey|token|webhook"
_SENSITIVE_QUERY_RE = re.compile(rf"(?i)(\b(?:{_SENSITIVE_NAMES})=)([^&\s]+)")
_SENSITIVE_FIELD_RE = re.compile(
    rf"(?i)(['\"]?\b(?:{_SENSITIVE_NAMES})\b['\"]?\s*[:=]\s*['\"]?)"
    r"([^'\",\s}&]+)(['\"]?)"
)


def redact_sensitive_text(provider: Any, text: str) -> str:
    redacted = str(text)
    for field_name in provider_secret_fields(provider.type):
        value = str(provider.config.get(field_name) or "").strip()
        if value:
            redacted = redacted.replace(value, "[已脱敏]")
            redacted = redacted.replace(urllib.parse.quote_plus(value), "[已脱敏]")
            redacted = redacted.replace(urllib.parse.quote(value, safe=""), "[已脱敏]")
    redacted = _SENSITIVE_QUERY_RE.sub(r"\1[已脱敏]", redacted)
    return _SENSITIVE_FIELD_RE.sub(r"\1[已脱敏]\3", redacted)
