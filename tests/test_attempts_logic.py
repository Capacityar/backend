"""Tests de la lógica de attempts: evaluación, resolución de ejercicio y mastery.

Aislados: repositorio y Session se mockean, no hay DB real ni red.
"""

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.attempts import service
from app.modules.attempts.schemas import AttemptCreate


# ─── _evaluate ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "student, expected, etype, result",
    [
        ("  b ", "B", "multiple_choice", True),   # case-insensitive + trim
        ("a", "B", "multiple_choice", False),
        ("Hola Mundo", "hola mundo", "text", True),
        ("algo", "otra cosa", "text", False),
    ],
)
def test_evaluate(student, expected, etype, result):
    assert service._evaluate(student, expected, etype) is result


# ─── _resolve_exercise ─────────────────────────────────────────────────────────

def _plan():
    return {
        "modules": [
            {
                "skill_name": "Git",
                "units": [
                    {"exercises": [{"expected_answer": "x", "prompt": "p", "type": "text"}]}
                ],
            }
        ]
    }


def test_resolve_exercise_ok():
    ex = service._resolve_exercise(_plan(), 0, 0, 0)
    assert ex.skill_name == "Git"
    assert ex.expected_answer == "x"
    assert ex.type == "text"


@pytest.mark.parametrize("m, u, e", [(1, 0, 0), (0, 1, 0), (0, 0, 1)])
def test_resolve_exercise_out_of_range(m, u, e):
    with pytest.raises(HTTPException) as exc:
        service._resolve_exercise(_plan(), m, u, e)
    assert exc.value.status_code == 404


# ─── _compute_skill_mastery ────────────────────────────────────────────────────

def test_compute_mastery_empty(monkeypatch):
    monkeypatch.setattr(service.repository, "find_by_student_and_skill", lambda *a, **k: [])
    assert service._compute_skill_mastery(object(), "ana@x.com", "Git") == 0.0


def test_compute_mastery_ratio(monkeypatch):
    rows = [SimpleNamespace(is_correct=True), SimpleNamespace(is_correct=False),
            SimpleNamespace(is_correct=True)]
    monkeypatch.setattr(service.repository, "find_by_student_and_skill", lambda *a, **k: rows)
    assert service._compute_skill_mastery(object(), "ana@x.com", "Git") == pytest.approx(0.6667)


# ─── _serialize ────────────────────────────────────────────────────────────────

def test_serialize_threshold():
    attempt = SimpleNamespace(
        id=1, student_email="a@x.com", learning_path_id=1, module_index=0,
        unit_index=0, exercise_index=0, skill_name="Git", answer="a",
        expected_answer="a", is_correct=True, score=1.0, ai_feedback="ok",
        created_at=None,
    )
    assert service._serialize(attempt, 0.8)["mastery_threshold_reached"] is True
    assert service._serialize(attempt, 0.79)["mastery_threshold_reached"] is False


# ─── create_attempt / get_attempt / list (con Session y repo mockeados) ─────────

class _FakeSession:
    def __init__(self, path):
        self._path = path

    def get(self, model, pk):
        return self._path

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def _path_obj():
    plan = {
        "modules": [
            {
                "skill_name": "Git",
                "units": [
                    {"exercises": [{"expected_answer": "ok", "prompt": "p",
                                    "type": "text"}]}
                ],
            }
        ]
    }
    return SimpleNamespace(
        student_email="ana@example.com", student_name="Ana", plan_json=json.dumps(plan)
    )


def test_create_attempt_correct(monkeypatch):
    monkeypatch.setattr(service.repository, "create", lambda db, a: a)
    monkeypatch.setattr(service.repository, "find_by_student_and_skill",
                        lambda *a, **k: [SimpleNamespace(is_correct=True)])
    data = AttemptCreate(
        student_email="ana@example.com", learning_path_id=1, module_index=0,
        unit_index=0, exercise_index=0, answer="ok",
    )
    result = service.create_attempt(_FakeSession(_path_obj()), data)
    assert result["is_correct"] is True
    assert result["skill_name"] == "Git"
    assert result["skill_mastery"] == 1.0


def test_create_attempt_wrong_student(monkeypatch):
    data = AttemptCreate(
        student_email="otro@example.com", learning_path_id=1, module_index=0,
        unit_index=0, exercise_index=0, answer="ok",
    )
    with pytest.raises(HTTPException) as exc:
        service.create_attempt(_FakeSession(_path_obj()), data)
    assert exc.value.status_code == 403


def test_create_attempt_path_not_found(monkeypatch):
    data = AttemptCreate(
        student_email="ana@example.com", learning_path_id=1, module_index=0,
        unit_index=0, exercise_index=0, answer="ok",
    )
    with pytest.raises(HTTPException) as exc:
        service.create_attempt(_FakeSession(None), data)
    assert exc.value.status_code == 404


def test_get_attempt_not_found(monkeypatch):
    monkeypatch.setattr(service.repository, "find_by_id", lambda db, i: None)
    with pytest.raises(HTTPException) as exc:
        service.get_attempt(object(), 99)
    assert exc.value.status_code == 404


def test_list_attempts_caches_mastery(monkeypatch):
    rows = [
        SimpleNamespace(id=1, student_email="a@x.com", learning_path_id=1, module_index=0,
                        unit_index=0, exercise_index=0, skill_name="Git", answer="a",
                        expected_answer="a", is_correct=True, score=1.0, ai_feedback="",
                        created_at=None),
        SimpleNamespace(id=2, student_email="a@x.com", learning_path_id=1, module_index=0,
                        unit_index=1, exercise_index=0, skill_name="Git", answer="b",
                        expected_answer="b", is_correct=True, score=1.0, ai_feedback="",
                        created_at=None),
    ]
    monkeypatch.setattr(service.repository, "find_by_student", lambda *a, **k: rows)
    calls = []
    monkeypatch.setattr(service.repository, "find_by_student_and_skill",
                        lambda db, e, s: calls.append(s) or [SimpleNamespace(is_correct=True)])
    out = service.list_attempts_by_student(object(), "a@x.com")
    assert len(out) == 2
    assert calls == ["Git"]  # mastery de "Git" calculada una sola vez (cache)


def test_list_attempts_empty(monkeypatch):
    monkeypatch.setattr(service.repository, "find_by_student", lambda *a, **k: [])
    assert service.list_attempts_by_student(object(), "a@x.com") == []
