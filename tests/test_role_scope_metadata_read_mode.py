from __future__ import annotations

from app.core.config import settings
from app.core.decision import role_scope_metadata as role_scope_metadata_module


def _set_base_flags(monkeypatch) -> None:
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_CACHE_TTL_SEC", 60)
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_PATH", "dummy/path.json")


def test_db_mode_reads_published_metadata_and_caches(monkeypatch):
    _set_base_flags(monkeypatch)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_ENABLED", True)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_READ_MODE", "db")
    role_scope_metadata_module.reset_role_scope_metadata_cache()

    calls = {"db": 0, "file": 0}

    def _db_loader():
        calls["db"] += 1
        return {"source": "db", "version": "x"}

    def _file_loader(_):
        calls["file"] += 1
        return {"source": "file"}

    monkeypatch.setattr(role_scope_metadata_module, "_load_metadata_from_db", _db_loader)
    monkeypatch.setattr(role_scope_metadata_module, "_load_metadata_from_file", _file_loader)

    first = role_scope_metadata_module.get_role_scope_metadata()
    first["source"] = "mutated-client-copy"
    second = role_scope_metadata_module.get_role_scope_metadata()

    assert second["source"] == "db"
    assert calls["db"] == 1
    assert calls["file"] == 0


def test_db_mode_falls_back_to_file_when_db_unavailable(monkeypatch):
    _set_base_flags(monkeypatch)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_ENABLED", True)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_READ_MODE", "db")
    role_scope_metadata_module.reset_role_scope_metadata_cache()

    calls = {"db": 0, "file": 0}

    def _db_loader():
        calls["db"] += 1
        return None

    def _file_loader(_):
        calls["file"] += 1
        return {"source": "file", "version": "fallback"}

    monkeypatch.setattr(role_scope_metadata_module, "_load_metadata_from_db", _db_loader)
    monkeypatch.setattr(role_scope_metadata_module, "_load_metadata_from_file", _file_loader)

    payload = role_scope_metadata_module.get_role_scope_metadata()

    assert payload["source"] == "file"
    assert calls["db"] == 1
    assert calls["file"] == 1


def test_db_read_mode_has_no_effect_when_framework_disabled(monkeypatch):
    _set_base_flags(monkeypatch)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_ENABLED", False)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_READ_MODE", "db")
    role_scope_metadata_module.reset_role_scope_metadata_cache()

    def _db_loader():
        raise AssertionError("DB reader should not run when framework is disabled")

    monkeypatch.setattr(role_scope_metadata_module, "_load_metadata_from_db", _db_loader)
    monkeypatch.setattr(
        role_scope_metadata_module,
        "_load_metadata_from_file",
        lambda _: {"source": "file-legacy"},
    )

    payload = role_scope_metadata_module.get_role_scope_metadata()
    assert payload["source"] == "file-legacy"
