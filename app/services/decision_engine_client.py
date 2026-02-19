from __future__ import annotations

from typing import Any

import requests

from app.core.config import settings
from app.services.decision_engine_auth import resolve_decision_engine_bearer_token


def _normalize_evaluate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    table_slug = str(payload.get("table_slug") or "").strip()
    if not table_slug:
        raise ValueError("Decision engine evaluate payload missing required field 'table_slug'.")

    raw_context = payload.get("context")
    if raw_context is None:
        context: dict[str, Any] = {}
    elif isinstance(raw_context, dict):
        context = raw_context
    else:
        raise ValueError("Decision engine evaluate payload field 'context' must be an object.")

    normalized = dict(payload)
    normalized["table_slug"] = table_slug
    normalized["context"] = context
    return normalized


def post_evaluate(
    payload: dict[str, Any],
    *,
    timeout_seconds: float = 10,
    decision_engine_url: str | None = None,
) -> requests.Response:
    base_url = (decision_engine_url or settings.DECISION_ENGINE_URL).rstrip("/")
    url = f"{base_url}/evaluate"
    normalized_payload = _normalize_evaluate_payload(payload)

    headers: dict[str, str] = {}
    token = resolve_decision_engine_bearer_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(
        url,
        json=normalized_payload,
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
