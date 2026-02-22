from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from app.core.config import settings


def _xlsx_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['id'])
    sheet.append([1])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _event_lookup_xlsx_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "event_code",
            "event_name",
            "event_type",
            "application_object",
            "is_active",
        ]
    )
    sheet.append(["EVT_TEST_001", "Test Event", "EXPECTED", "PURCHASE_ORDER", True])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_datasets_list_includes_customer_and_company_master(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", False)
    monkeypatch.setattr(settings, "MASS_CHANGE_ENABLED", True)

    response = client.get("/mass-change/datasets", headers={"X-User-Email": "admin@example.com"})
    assert response.status_code == 200
    datasets = response.json().get("datasets") or []
    keys = {row.get("dataset_key") for row in datasets}
    assert "customer_master" in keys
    assert "company_master" in keys
    assert "users" in keys


def test_phase1_datasets_allow_template_validate_submit(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", False)
    monkeypatch.setattr(settings, "MASS_CHANGE_ENABLED", True)

    headers = {"X-User-Email": "admin@example.com"}

    template_resp = client.get("/mass-change/event_lookup/template.xlsx", headers=headers)
    assert template_resp.status_code == 200


    validate_resp = client.post(
        "/mass-change/event_lookup/validate?filename=sample.xlsx",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=_event_lookup_xlsx_bytes(),
    )
    assert validate_resp.status_code == 200
    validate_payload = validate_resp.json()
    assert validate_payload.get("eligible_to_submit") is True
    batch_id = str(validate_payload.get("batch_id") or "")
    assert batch_id

    submit_resp = client.post(
        "/mass-change/event_lookup/submit",
        headers=headers,
        json={"batch_id": batch_id},
    )
    assert submit_resp.status_code == 200
    submit_payload = submit_resp.json()
    summary = submit_payload.get("summary") or {}
    assert summary.get("processed") == 1
    assert summary.get("created") == 1
    assert summary.get("failed") == 0


def test_enabled_dataset_template_still_available(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", False)
    monkeypatch.setattr(settings, "MASS_CHANGE_ENABLED", True)

    response = client.get("/mass-change/users/template.xlsx", headers={"X-User-Email": "admin@example.com"})
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
