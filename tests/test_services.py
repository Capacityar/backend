"""Tests de servicios (users, job_descriptions, user_skills) con repos mockeados."""

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.job_descriptions import service as jd_service
from app.modules.user_skills import service as us_service
from app.modules.users import service as users_service
from app.modules.users.models import UserRole


# ─── users ─────────────────────────────────────────────────────────────────────

def test_get_user_not_found(monkeypatch):
    monkeypatch.setattr(users_service.repository, "find_by_id", lambda db, i: None)
    with pytest.raises(HTTPException) as e:
        users_service.get_user(object(), 1)
    assert e.value.status_code == 404


def test_create_user_conflict(monkeypatch):
    monkeypatch.setattr(users_service.repository, "find_by_email", lambda db, e: object())
    with pytest.raises(HTTPException) as e:
        users_service.create_user(object(), SimpleNamespace(email="a@x.com"))
    assert e.value.status_code == 409


def test_create_user_ok(monkeypatch):
    monkeypatch.setattr(users_service.repository, "find_by_email", lambda db, e: None)
    monkeypatch.setattr(users_service.repository, "create", lambda db, d: SimpleNamespace(id=1))
    assert users_service.create_user(object(), SimpleNamespace(email="a@x.com")).id == 1


def test_update_user_email_conflict(monkeypatch):
    monkeypatch.setattr(users_service.repository, "find_by_id", lambda db, i: SimpleNamespace(id=1))
    monkeypatch.setattr(users_service.repository, "find_by_email",
                        lambda db, e: SimpleNamespace(id=2))
    with pytest.raises(HTTPException) as e:
        users_service.update_user(object(), 1, SimpleNamespace(email="other@x.com"))
    assert e.value.status_code == 409


def test_delete_user_calls_repo(monkeypatch):
    user = SimpleNamespace(id=1)
    monkeypatch.setattr(users_service.repository, "find_by_id", lambda db, i: user)
    deleted = []
    monkeypatch.setattr(users_service.repository, "delete", lambda db, u: deleted.append(u))
    users_service.delete_user(object(), 1)
    assert deleted == [user]


# ─── job_descriptions ──────────────────────────────────────────────────────────

def test_create_jd_user_not_found(monkeypatch):
    monkeypatch.setattr(jd_service.users_repository, "find_by_id", lambda db, i: None)
    with pytest.raises(HTTPException) as e:
        jd_service.create_job_description(object(), SimpleNamespace(user_id=1))
    assert e.value.status_code == 404


def test_create_jd_forbidden_for_non_admin(monkeypatch):
    monkeypatch.setattr(jd_service.users_repository, "find_by_id",
                        lambda db, i: SimpleNamespace(role=UserRole.student))
    with pytest.raises(HTTPException) as e:
        jd_service.create_job_description(object(), SimpleNamespace(user_id=1))
    assert e.value.status_code == 403


def test_create_jd_ok(monkeypatch):
    admin = SimpleNamespace(id=1, role=UserRole.company_admin, first_name="C",
                            last_name="A", email="c@x.com")
    jd = SimpleNamespace(id=5, title="Dev", description="d", province="CABA",
                         user_id=1, created_at=datetime(2026, 1, 1))
    monkeypatch.setattr(jd_service.users_repository, "find_by_id", lambda db, i: admin)
    monkeypatch.setattr(jd_service.repository, "create", lambda db, d: jd)
    monkeypatch.setattr(jd_service.repository, "find_skills_for_jd",
                        lambda db, i: [(1, "Python", "INTERMEDIATE")])
    resp = jd_service.create_job_description(object(), SimpleNamespace(user_id=1))
    assert resp.id == 5
    assert resp.posted_by.email == "c@x.com"
    assert resp.required_skills[0].skill_name == "Python"


def test_build_response_handles_deleted_user(monkeypatch):
    jd = SimpleNamespace(id=5, title="Dev", description="d", province="CABA",
                         user_id=99, created_at=datetime(2026, 1, 1))
    monkeypatch.setattr(jd_service.users_repository, "find_by_id", lambda db, i: None)
    monkeypatch.setattr(jd_service.repository, "find_skills_for_jd", lambda db, i: [])
    resp = jd_service._build_response(object(), jd)
    assert resp.posted_by.first_name == "[Eliminado]"


def test_delete_jd_not_found(monkeypatch):
    monkeypatch.setattr(jd_service.repository, "find_by_id", lambda db, i: None)
    with pytest.raises(HTTPException) as e:
        jd_service.delete_job_description(object(), 1)
    assert e.value.status_code == 404


# ─── user_skills ─────────────────────────────────────────────────────────────

def test_list_for_user_not_found(monkeypatch):
    monkeypatch.setattr(us_service.users_repository, "find_by_email", lambda db, e: None)
    with pytest.raises(HTTPException) as e:
        us_service.list_for_user(object(), "a@x.com")
    assert e.value.status_code == 404


def test_add_skill_conflict(monkeypatch):
    monkeypatch.setattr(us_service.users_repository, "find_by_email",
                        lambda db, e: SimpleNamespace(id=1))
    monkeypatch.setattr(us_service.repository, "find_one", lambda db, u, s: object())
    with pytest.raises(HTTPException) as e:
        us_service.add_skill(object(), "a@x.com", SimpleNamespace(skill_id=1, level=2))
    assert e.value.status_code == 409


def test_remove_skill_not_in_list(monkeypatch):
    monkeypatch.setattr(us_service.users_repository, "find_by_email",
                        lambda db, e: SimpleNamespace(id=1))
    monkeypatch.setattr(us_service.repository, "remove", lambda db, u, s: False)
    with pytest.raises(HTTPException) as e:
        us_service.remove_skill(object(), "a@x.com", 1)
    assert e.value.status_code == 404
