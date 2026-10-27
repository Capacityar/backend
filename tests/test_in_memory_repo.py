"""Tests del repositorio in-memory de learning paths (sin DB)."""

from app.modules.learning_paths.plan_generator.mock import MockPlanGenerator
from app.modules.learning_paths.repository.in_memory import (
    InMemoryLearningPathRepository,
)
from app.modules.learning_paths.schemas import PathStatus


def _plan(gap_report):
    return MockPlanGenerator().generate(gap_report)


def test_save_assigns_id_and_status(gap_report):
    repo = InMemoryLearningPathRepository()
    stored = repo.save(_plan(gap_report))
    assert stored.id == 1
    assert stored.status == PathStatus.ACTIVE
    assert repo.save(_plan(gap_report)).id == 2  # ids incrementales


def test_find_by_id(gap_report):
    repo = InMemoryLearningPathRepository()
    stored = repo.save(_plan(gap_report))
    assert repo.find_by_id(stored.id) is stored
    assert repo.find_by_id(999) is None


def test_find_by_student_email_case_insensitive(gap_report):
    repo = InMemoryLearningPathRepository()
    repo.save(_plan(gap_report))
    assert len(repo.find_by_student_email("ANA@example.com")) == 1
    assert repo.find_by_student_email("nadie@x.com") == []


def test_list_all_pagination(gap_report):
    repo = InMemoryLearningPathRepository()
    for _ in range(3):
        repo.save(_plan(gap_report))
    assert [p.id for p in repo.list_all(offset=1, limit=1)] == [2]
    assert len(repo.list_all()) == 3
