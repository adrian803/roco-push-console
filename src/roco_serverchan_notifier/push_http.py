from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests

from .push_models import ProviderConfig, PushResult
from .push_redaction import redact_sensitive_text

HttpSession = requests.Session


@dataclass(frozen=True)
class JsonPostRequest:
    provider: ProviderConfig
    session: HttpSession
    url: str
    payload: dict[str, Any]
    timeout: int
    headers: dict[str, str] | None = None
    success_codes: set[Any] = field(default_factory=lambda: {0, "0"})


def json_result(payload: dict[str, Any], success_codes: set[Any]) -> tuple[bool, str]:
    code = payload.get("code", payload.get("errcode"))
    success = code in success_codes
    if code is None and not payload:
        success = True
    message = str(payload.get("message") or payload.get("msg") or payload.get("errmsg") or payload)
    return success, message


def result_from_response(
    provider: ProviderConfig,
    response: requests.Response,
    *,
    success_codes: set[Any],
) -> PushResult:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    success, message = json_result(payload, success_codes)
    if response.status_code >= 400:
        success = False
        message = response.text[:200] or message
    return PushResult(
        provider.id,
        provider.name,
        provider.type,
        success,
        redact_sensitive_text(provider, message),
        response.status_code,
    )


def post_json(request: JsonPostRequest) -> PushResult:
    response = request.session.post(
        request.url,
        json=request.payload,
        headers=request.headers,
        timeout=request.timeout,
    )
    return result_from_response(
        request.provider,
        response,
        success_codes=request.success_codes,
    )
