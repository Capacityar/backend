# ruff: noqa: E402
"""Config y fixtures compartidas para la suite.

Setea variables de entorno antes de importar la app para que los tests corran
aislados: SQLite en el tmp del SO (no PostgreSQL ni red) y generador de planes
en mock. Las fixtures de base de datos usan SQLite en memoria.
"""

import os
import tempfile

_db_path = os.path.join(tempfile.gettempdir(), "capacity_ar_test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")
os.environ.setdefault("PLAN_GENERATOR", "mock")

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.database
from app.config import settings
from app.database import Base, get_db
from app.main import app as fastapi_app
from app.modules.learning_paths.plan_generator.factory import get_plan_generator
from app.modules.learning_paths.plan_generator.mock import MockPlanGenerator
from app.modules.learning_paths.schemas import (
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

# Ensure all SQLAlchemy models are registered on Base.metadata
import app.modules.attempts.models
import app.modules.gap_analysis.models
import app.modules.job_descriptions.models
import app.modules.learning_paths.models
import app.modules.resources.models
import app.modules.skills.models
import app.modules.users.models
import app.modules.user_skills.models

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def force_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enforce strictly offline, in-memory configuration across all tests."""
    monkeypatch.setattr(settings, "plan_generator", "mock")
    monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    monkeypatch.setattr(app.database, "engine", engine)
    monkeypatch.setattr(app.database, "SessionLocal", TestingSessionLocal)
    # app.main importa SessionLocal por valor: hay que reapuntarlo para que el
    # lifespan (create_db_tables + seed) use el engine en memoria y no el de disco.
    monkeypatch.setattr("app.main.SessionLocal", TestingSessionLocal)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        try:
            session.rollback()
        except Exception:
            pass
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        if not db_session.is_active:
            try:
                db_session.rollback()
            except Exception:
                pass
        try:
            yield db_session
        finally:
            try:
                db_session.rollback()
            except Exception:
                pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_plan_generator] = lambda: MockPlanGenerator()
    test_client = TestClient(fastapi_app)
    try:
        yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()


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
