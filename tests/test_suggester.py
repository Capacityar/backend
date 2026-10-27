"""Tests del suggester de recursos: resolución de URLs, whitelist y modo mock."""

import pytest

from app.modules.resources import suggester
from app.shared.llm import LlmConfigurationError


# ─── _resolve_url ──────────────────────────────────────────────────────────────

def test_resolve_url_canonical_whitelisted():
    item = {"canonical_url": "https://developer.mozilla.org/es/docs/Web/HTML", "type": "guide"}
    assert suggester._resolve_url(item, "HTML") == item["canonical_url"]


def test_resolve_url_canonical_not_whitelisted_falls_back_to_search():
    item = {"canonical_url": "https://sitio-random.com/x", "type": "guide",
            "search_terms": "html basico"}
    url = suggester._resolve_url(item, "HTML")
    assert url.startswith("https://www.google.com/search?q=")
    assert "html+basico" in url


def test_resolve_url_video_uses_youtube():
    item = {"type": "video", "search_terms": "git tutorial"}
    url = suggester._resolve_url(item, "Git")
    assert url.startswith("https://www.youtube.com/results?search_query=")


def test_resolve_url_defaults_query_to_skill_and_title():
    item = {"type": "guide", "title": "Guía"}
    url = suggester._resolve_url(item, "Git")
    assert "Git" in url and "Gu" in url


# ─── _mock_resources ───────────────────────────────────────────────────────────

def test_mock_resources_pasion():
    res = suggester._mock_resources("Python", "pasion")
    assert [r.type for r in res] == ["video", "reading"]
    assert res[0].url.startswith("https://www.youtube.com/results")
    assert all(r.generated_by == "mock" for r in res)


def test_mock_resources_practica():
    res = suggester._mock_resources("Python", "practica")
    assert len(res) == 2
    assert all(r.type == "guide" for r in res)


def test_mock_resources_unknown_phase():
    assert suggester._mock_resources("Python", "inexistente") == []


# ─── suggest_resources (modo mock) ─────────────────────────────────────────────

def test_suggest_resources_unknown_phase_returns_empty(monkeypatch):
    monkeypatch.setattr(suggester.settings, "plan_generator", "mock")
    assert suggester.suggest_resources("Python", "fase-rara") == []


def test_suggest_resources_mock_mode(monkeypatch):
    monkeypatch.setattr(suggester.settings, "plan_generator", "mock")
    res = suggester.suggest_resources("Python", "pasion")
    assert len(res) == 2
    assert res[0].skill_name == "Python"


def test_build_client_raises_in_mock_mode(monkeypatch):
    monkeypatch.setattr(suggester.settings, "plan_generator", "mock")
    with pytest.raises(LlmConfigurationError):
        suggester._build_client()
