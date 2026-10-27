"""Config y fixtures compartidas para la suite.

Setea env antes de importar la app para que los tests corran aislados:
SQLite en el tmp del SO (no PostgreSQL ni red) y generador de planes en mock.
"""

import os
import tempfile

_db_path = os.path.join(tempfile.gettempdir(), "capacity_ar_test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")
os.environ.setdefault("PLAN_GENERATOR", "mock")

import pytest  # noqa: E402

from app.modules.learning_paths.schemas import (  # noqa: E402
    CompanyInput,
    GapReport,
    GapSkill,
    RequiredSkill,
    SkillPriority,
    SkillStatus,
    StudentInput,
    StudentSkill,
    TargetRoleInput,
)


def make_gap_report() -> GapReport:
    """GapReport con una skill READY (se ignora) y dos a entrenar (HIGH y LOW)."""
    return GapReport(
        id=7,
        student=StudentInput(
            name="Ana",
            email="ana@example.com",
            skills=[StudentSkill(name="Python", level=1)],
            interests=["videojuegos"],
        ),
        company=CompanyInput(name="ACME"),
        target_role=TargetRoleInput(
            title="Dev Junior",
            required_skills=[RequiredSkill(name="Python", level=4, priority=SkillPriority.LOW)],
        ),
        summary="resumen",
        readiness_score=40,
        skills=[
            GapSkill(
                name="Python",
                current_level=1,
                required_level=4,
                gap_level=3,
                priority=SkillPriority.LOW,
                status=SkillStatus.NEEDS_WORK,
            ),
            GapSkill(
                name="Git",
                current_level=0,
                required_level=3,
                gap_level=3,
                priority=SkillPriority.HIGH,
                status=SkillStatus.MISSING,
            ),
            GapSkill(
                name="HTML",
                current_level=5,
                required_level=3,
                gap_level=-2,
                priority=SkillPriority.LOW,
                status=SkillStatus.READY,
            ),
        ],
    )


@pytest.fixture
def gap_report() -> GapReport:
    return make_gap_report()
