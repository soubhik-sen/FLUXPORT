from __future__ import annotations

from typing import Any

import requests

from app.core.config import settings
from app.services.decision_engine_auth import resolve_decision_engine_bearer_token


def post_evaluate(
    payload: dict[str, Any],
    *,
    timeout_seconds: float = 10,
    decision_engine_url: str | None = None,
) -> requests.Response:
    base_url = (decision_engine_url or settings.DECISION_ENGINE_URL).rstrip("/")
    url = f"{base_url}/evaluate"

    headers: dict[str, str] = {}
    token = resolve_decision_engine_bearer_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(
        url,
        json=payload,
        headers=headers or None,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response


def evaluate(
    payload: dict[str, Any],
    *,
    timeout_seconds: float = 10,
    decision_engine_url: str | None = None,
) -> dict[str, Any]:
    response = post_evaluate(
        payload,
        timeout_seconds=timeout_seconds,
        decision_engine_url=decision_engine_url,
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise requests.RequestException("Decision engine returned invalid JSON.") from exc
    if not isinstance(body, dict):
        raise requests.RequestException("Decision engine returned a non-object JSON payload.")
    return body
