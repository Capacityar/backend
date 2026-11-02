# Job Descriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar módulos `skills` y `job_descriptions` al backend FastAPI, y dos páginas al frontend React (`/new-job` y `/jobs`) que permiten a un `company_admin` publicar y listar descripciones de puestos IT.

**Architecture:** Dos módulos nuevos en `app/modules/` siguiendo el patrón existente (router → service → repository → models → schemas). La tabla `skills` sirve como catálogo para el autocomplete; `job_descriptions` + `job_description_skills` (association table) almacenan las JDs con sus skills requeridas. El frontend usa TanStack Query para el listado y estado local para el formulario.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, pytest + httpx (TestClient), React + wouter + TanStack Query, shadcn/ui (Input, Textarea, Select, Button, Badge), TypeScript.

---

## File Map

### Backend — crear
- `tests/__init__.py`
- `tests/conftest.py` — TestClient con SQLite in-memory, override de `get_db`
- `tests/test_skills.py` — tests de skills (HTTP level)
- `tests/test_job_descriptions.py` — tests de job descriptions (HTTP level)
- `app/modules/skills/__init__.py`
- `app/modules/skills/models.py` — modelo `Skill`
- `app/modules/skills/schemas.py` — `SkillCreate`, `SkillResponse`
- `app/modules/skills/repository.py` — queries SQLAlchemy
- `app/modules/skills/service.py` — `search`, `get_or_create`
- `app/modules/skills/seed.py` — `seed_skills_if_empty` con ~70 skills IT
- `app/modules/skills/router.py` — `GET /skills`, `POST /skills`
- `app/modules/job_descriptions/__init__.py`
- `app/modules/job_descriptions/models.py` — `SkillLevel` enum, `JobDescription`, `JobDescriptionSkill`
- `app/modules/job_descriptions/schemas.py` — `JobDescriptionCreate`, `JobDescriptionResponse`, sub-schemas
- `app/modules/job_descriptions/repository.py` — queries SQLAlchemy
- `app/modules/job_descriptions/service.py` — orquesta crear/listar/borrar + construye respuesta
- `app/modules/job_descriptions/router.py` — `POST/GET /job-descriptions`, `DELETE /job-descriptions/{id}`

### Backend — modificar
- `app/main.py` — registrar routers nuevos, llamar seed en lifespan

### Frontend — crear
- `frontend/src/lib/constants.ts` — `ARGENTINIAN_PROVINCES`, `SKILL_LEVELS`, `LEVEL_LABELS`, `LEVEL_COLORS`
- `frontend/src/pages/NuevoPuesto.tsx` — formulario `/new-job`
- `frontend/src/pages/ListadoPuestos.tsx` — listado `/jobs`

### Frontend — modificar
- `frontend/src/lib/api.ts` — tipos e helpers para skills y job descriptions
- `frontend/src/components/AppLayout.tsx` — rol `"empresa"` con sus links
- `frontend/src/App.tsx` — rutas `/new-job` y `/jobs`

---

## Task 1: Infraestructura de tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Instalar dev dependencies**

```bash
cd /home/dev/capacitaya
source .venv/bin/activate
pip install -e ".[dev]"
```

Esperado: `Successfully installed pytest-8.3.4 httpx-0.28.1` (o similar — ya instalados = OK también).

- [ ] **Step 2: Crear `tests/__init__.py`**

Archivo vacío:

```python
```

- [ ] **Step 3: Crear `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

_TEST_DB_URL = "sqlite:///./test_capacity.db"
_engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})


@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestingSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=_engine)

    def _override_get_db():
        db = _TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_engine)
```

- [ ] **Step 4: Verificar que pytest corre sin errores (sin tests aún)**

```bash
pytest --collect-only
```

Esperado: `no tests ran` o `0 tests collected` — sin errores de import.

---

## Task 2: Módulo `skills` — models, schemas, repository

**Files:**
- Create: `app/modules/skills/__init__.py`
- Create: `app/modules/skills/models.py`
- Create: `app/modules/skills/schemas.py`
- Create: `app/modules/skills/repository.py`

- [ ] **Step 1: Crear `app/modules/skills/__init__.py`**

Archivo vacío.

- [ ] **Step 2: Crear `app/modules/skills/models.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Crear `app/modules/skills/schemas.py`**

```python
from pydantic import BaseModel, ConfigDict, Field


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SkillResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Crear `app/modules/skills/repository.py`**

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.skills.models import Skill
from app.modules.skills.schemas import SkillCreate


def find_by_name_ilike(db: Session, name: str) -> Skill | None:
    statement = select(Skill).where(Skill.name.ilike(name))
    return db.scalar(statement)


def search(db: Session, q: str, limit: int = 20) -> list[Skill]:
    statement = (
        select(Skill)
        .where(Skill.name.ilike(f"%{q}%"))
        .order_by(Skill.name)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def create(db: Session, data: SkillCreate) -> Skill:
    skill = Skill(name=data.name)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Skill)) or 0


def bulk_create(db: Session, names: list[str]) -> None:
    db.add_all([Skill(name=name) for name in names])
    db.commit()
```

---

## Task 3: Módulo `skills` — service, seed, router

**Files:**
- Create: `app/modules/skills/service.py`
- Create: `app/modules/skills/seed.py`
- Create: `app/modules/skills/router.py`
- Create: `tests/test_skills.py`

- [ ] **Step 1: Crear `app/modules/skills/service.py`**

```python
from sqlalchemy.orm import Session

from app.modules.skills import repository
from app.modules.skills.models import Skill
from app.modules.skills.schemas import SkillCreate


def search(db: Session, q: str) -> list[Skill]:
    return repository.search(db, q)


def get_or_create(db: Session, data: SkillCreate) -> tuple[Skill, bool]:
    """Returns (skill, created). created=True if the skill is new."""
    existing = repository.find_by_name_ilike(db, data.name)
    if existing is not None:
        return existing, False
    return repository.create(db, data), True
```

- [ ] **Step 2: Crear `app/modules/skills/seed.py`**

```python
from sqlalchemy.orm import Session

from app.modules.skills import repository

_INITIAL_SKILLS: list[str] = [
    # Lenguajes
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C#", "PHP",
    "Ruby", "Kotlin", "Swift",
    # Frameworks web
    "React", "Vue", "Angular", "Next.js", "FastAPI", "Django", "Spring Boot",
    "Laravel", "Rails", "Express", "NestJS",
    # Bases de datos
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Elasticsearch",
    "DynamoDB",
    # DevOps / infra
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "Ansible",
    "GitHub Actions", "Linux",
    # Datos / IA
    "SQL", "Pandas", "NumPy", "TensorFlow", "PyTorch", "Scikit-learn",
    "Apache Spark", "dbt", "Airflow",
    # Herramientas generales
    "Git", "REST APIs", "GraphQL", "gRPC", "Agile/Scrum", "Jira", "Figma",
]


def seed_skills_if_empty(db: Session) -> None:
    if repository.count(db) == 0:
        repository.bulk_create(db, _INITIAL_SKILLS)
```

- [ ] **Step 3: Crear `app/modules/skills/router.py`**

```python
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.skills import service
from app.modules.skills.schemas import SkillCreate, SkillResponse

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
def search_skills(
    q: str = Query(default="", max_length=200),
    db: Session = Depends(get_db),
) -> list[SkillResponse]:
    return service.search(db, q)


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: SkillCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> SkillResponse:
    skill, created = service.get_or_create(db, payload)
    if not created:
        response.status_code = status.HTTP_200_OK
    return skill
```

- [ ] **Step 4: Registrar el router en `app/main.py` temporalmente para que los tests funcionen**

Agregar al bloque de imports:

```python
from app.modules.skills.router import router as skills_router
```

Agregar al bloque de `include_router`, antes de la catch-all route:

```python
app.include_router(skills_router, prefix="/api")
```

Y en el lifespan, llamar al seed (requiere importar la sesión):

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.database import SessionLocal, create_db_tables
from app.modules.attempts.router import router as attempts_router, student_attempts_router
from app.modules.gap_analysis.router import router as gap_analysis_router, student_gap_analyses_router
from app.modules.learning_paths.router import router as learning_paths_router, student_paths_router
from app.modules.skills.router import router as skills_router
from app.modules.skills.seed import seed_skills_if_empty
from app.modules.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db_tables()
    db = SessionLocal()
    try:
        seed_skills_if_empty(db)
    finally:
        db.close()
    yield
```

**Nota:** el resto de `main.py` (include_router, frontend serve) no cambia hasta Task 7. Por ahora sólo agregar `skills_router`.

- [ ] **Step 5: Escribir los tests en `tests/test_skills.py`**

```python
def test_search_skills_returns_matching(client):
    client.post("/api/skills", json={"name": "Python"})
    client.post("/api/skills", json={"name": "JavaScript"})
    client.post("/api/skills", json={"name": "Java"})

    response = client.get("/api/skills?q=java")
    assert response.status_code == 200
    names = [s["name"] for s in response.json()]
    assert "JavaScript" in names
    assert "Java" in names
    assert "Python" not in names


def test_search_skills_empty_query_returns_nothing(client):
    client.post("/api/skills", json={"name": "Python"})
    response = client.get("/api/skills?q=")
    assert response.status_code == 200
    assert response.json() == []


def test_create_skill_returns_201(client):
    response = client.post("/api/skills", json={"name": "Python"})
    assert response.status_code == 201
    assert response.json()["name"] == "Python"
    assert "id" in response.json()


def test_create_skill_case_insensitive_dedup(client):
    r1 = client.post("/api/skills", json={"name": "Python"})
    assert r1.status_code == 201

    r2 = client.post("/api/skills", json={"name": "python"})
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

```bash
pytest tests/test_skills.py -v
```

Esperado:
```
PASSED tests/test_skills.py::test_search_skills_returns_matching
PASSED tests/test_skills.py::test_search_skills_empty_query_returns_nothing
PASSED tests/test_skills.py::test_create_skill_returns_201
PASSED tests/test_skills.py::test_create_skill_case_insensitive_dedup
4 passed
```

---

## Task 4: Módulo `job_descriptions` — models y schemas

**Files:**
- Create: `app/modules/job_descriptions/__init__.py`
- Create: `app/modules/job_descriptions/models.py`
- Create: `app/modules/job_descriptions/schemas.py`

- [ ] **Step 1: Crear `app/modules/job_descriptions/__init__.py`**

Archivo vacío.

- [ ] **Step 2: Crear `app/modules/job_descriptions/models.py`**

```python
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SkillLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    PRO = "PRO"


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class JobDescriptionSkill(Base):
    __tablename__ = "job_description_skills"

    job_description_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), primary_key=True
    )
    level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, name="skill_level"), nullable=False
    )
```

- [ ] **Step 3: Crear `app/modules/job_descriptions/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.job_descriptions.models import SkillLevel


class SkillRequirementIn(BaseModel):
    skill_id: int = Field(ge=1)
    level: SkillLevel


class SkillRequirementOut(BaseModel):
    skill_id: int
    skill_name: str
    level: SkillLevel


class PostedByResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


class JobDescriptionCreate(BaseModel):
    user_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    province: str = Field(min_length=1, max_length=100)
    required_skills: list[SkillRequirementIn] = Field(min_length=1)


class JobDescriptionResponse(BaseModel):
    id: int
    title: str
    description: str
    province: str
    posted_by: PostedByResponse
    required_skills: list[SkillRequirementOut]
    created_at: datetime
```

---

## Task 5: Módulo `job_descriptions` — repository y service

**Files:**
- Create: `app/modules/job_descriptions/repository.py`
- Create: `app/modules/job_descriptions/service.py`

- [ ] **Step 1: Crear `app/modules/job_descriptions/repository.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.job_descriptions.models import (
    JobDescription,
    JobDescriptionSkill,
    SkillLevel,
)
from app.modules.job_descriptions.schemas import JobDescriptionCreate
from app.modules.skills.models import Skill


def create(db: Session, data: JobDescriptionCreate) -> JobDescription:
    jd = JobDescription(
        user_id=data.user_id,
        title=data.title,
        description=data.description,
        province=data.province,
    )
    db.add(jd)
    db.flush()
    for req in data.required_skills:
        db.add(
            JobDescriptionSkill(
                job_description_id=jd.id,
                skill_id=req.skill_id,
                level=req.level,
            )
        )
    db.commit()
    db.refresh(jd)
    return jd


def find_all(db: Session, province: str | None = None) -> list[JobDescription]:
    statement = select(JobDescription).order_by(JobDescription.created_at.desc())
    if province:
        statement = statement.where(JobDescription.province == province)
    return list(db.scalars(statement).all())


def find_by_id(db: Session, jd_id: int) -> JobDescription | None:
    return db.get(JobDescription, jd_id)


def find_skills_for_jd(
    db: Session, jd_id: int
) -> list[tuple[int, str, SkillLevel]]:
    """Returns list of (skill_id, skill_name, level)."""
    statement = (
        select(JobDescriptionSkill.skill_id, Skill.name, JobDescriptionSkill.level)
        .join(Skill, Skill.id == JobDescriptionSkill.skill_id)
        .where(JobDescriptionSkill.job_description_id == jd_id)
    )
    return list(db.execute(statement).all())


def delete(db: Session, jd: JobDescription) -> None:
    db.delete(jd)
    db.commit()
```

- [ ] **Step 2: Crear `app/modules/job_descriptions/service.py`**

```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.job_descriptions import repository
from app.modules.job_descriptions.schemas import (
    JobDescriptionCreate,
    JobDescriptionResponse,
    PostedByResponse,
    SkillRequirementOut,
)
from app.modules.users import repository as users_repository
from app.modules.users.models import UserRole


def _build_response(db: Session, jd) -> JobDescriptionResponse:
    user = users_repository.find_by_id(db, jd.user_id)
    skills_rows = repository.find_skills_for_jd(db, jd.id)
    return JobDescriptionResponse(
        id=jd.id,
        title=jd.title,
        description=jd.description,
        province=jd.province,
        posted_by=PostedByResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
        ),
        required_skills=[
            SkillRequirementOut(skill_id=sid, skill_name=sname, level=level)
            for sid, sname, level in skills_rows
        ],
        created_at=jd.created_at,
    )


def create_job_description(
    db: Session, data: JobDescriptionCreate
) -> JobDescriptionResponse:
    user = users_repository.find_by_id(db, data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.role != UserRole.company_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company_admin users can post job descriptions",
        )
    jd = repository.create(db, data)
    return _build_response(db, jd)


def list_job_descriptions(
    db: Session, province: str | None = None
) -> list[JobDescriptionResponse]:
    jds = repository.find_all(db, province=province)
    return [_build_response(db, jd) for jd in jds]


def delete_job_description(db: Session, jd_id: int) -> None:
    jd = repository.find_by_id(db, jd_id)
    if jd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )
    repository.delete(db, jd)
```

---

## Task 6: Módulo `job_descriptions` — router + tests

**Files:**
- Create: `app/modules/job_descriptions/router.py`
- Create: `tests/test_job_descriptions.py`

- [ ] **Step 1: Crear `app/modules/job_descriptions/router.py`**

```python
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.job_descriptions import service
from app.modules.job_descriptions.schemas import (
    JobDescriptionCreate,
    JobDescriptionResponse,
)

router = APIRouter(prefix="/job-descriptions", tags=["job-descriptions"])


@router.post(
    "",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_description(
    payload: JobDescriptionCreate, db: Session = Depends(get_db)
) -> JobDescriptionResponse:
    return service.create_job_description(db, payload)


@router.get("", response_model=list[JobDescriptionResponse])
def list_job_descriptions(
    province: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> list[JobDescriptionResponse]:
    return service.list_job_descriptions(db, province=province)


@router.delete("/{jd_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_description(
    jd_id: int, db: Session = Depends(get_db)
) -> None:
    service.delete_job_description(db, jd_id)
```

- [ ] **Step 2: Escribir los tests en `tests/test_job_descriptions.py`**

```python
import pytest


@pytest.fixture
def company_admin(client):
    return client.post(
        "/api/users",
        json={
            "first_name": "Empresa",
            "last_name": "Global",
            "email": "empresa@test.com",
            "role": "company_admin",
        },
    ).json()


@pytest.fixture
def python_skill(client):
    return client.post("/api/skills", json={"name": "Python"}).json()


def test_create_job_description(client, company_admin, python_skill):
    response = client.post(
        "/api/job-descriptions",
        json={
            "user_id": company_admin["id"],
            "title": "Backend Developer Senior",
            "description": "Buscamos un backend developer con experiencia en APIs REST.",
            "province": "Buenos Aires",
            "required_skills": [
                {"skill_id": python_skill["id"], "level": "ADVANCED"}
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Backend Developer Senior"
    assert data["province"] == "Buenos Aires"
    assert data["posted_by"]["email"] == "empresa@test.com"
    assert len(data["required_skills"]) == 1
    assert data["required_skills"][0]["skill_name"] == "Python"
    assert data["required_skills"][0]["level"] == "ADVANCED"


def test_create_job_description_rejects_non_company_admin(client, python_skill):
    student = client.post(
        "/api/users",
        json={
            "first_name": "Lucía",
            "last_name": "Ramírez",
            "email": "lucia@test.com",
            "role": "student",
        },
    ).json()

    response = client.post(
        "/api/job-descriptions",
        json={
            "user_id": student["id"],
            "title": "Backend Developer",
            "description": "Descripción del puesto.",
            "province": "Córdoba",
            "required_skills": [{"skill_id": python_skill["id"], "level": "BEGINNER"}],
        },
    )
    assert response.status_code == 403


def test_create_job_description_rejects_unknown_user(client, python_skill):
    response = client.post(
        "/api/job-descriptions",
        json={
            "user_id": 9999,
            "title": "Backend Developer",
            "description": "Descripción.",
            "province": "Córdoba",
            "required_skills": [{"skill_id": python_skill["id"], "level": "BEGINNER"}],
        },
    )
    assert response.status_code == 404


def test_list_job_descriptions(client, company_admin, python_skill):
    client.post(
        "/api/job-descriptions",
        json={
            "user_id": company_admin["id"],
            "title": "JD 1",
            "description": "Desc.",
            "province": "Buenos Aires",
            "required_skills": [{"skill_id": python_skill["id"], "level": "BEGINNER"}],
        },
    )
    client.post(
        "/api/job-descriptions",
        json={
            "user_id": company_admin["id"],
            "title": "JD 2",
            "description": "Desc.",
            "province": "Córdoba",
            "required_skills": [{"skill_id": python_skill["id"], "level": "INTERMEDIATE"}],
        },
    )

    response = client.get("/api/job-descriptions")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_job_descriptions_filtered_by_province(client, company_admin, python_skill):
    client.post(
        "/api/job-descriptions",
        json={
            "user_id": company_admin["id"],
            "title": "JD Buenos Aires",
            "description": "Desc.",
            "province": "Buenos Aires",
            "required_skills": [{"skill_id": python_skill["id"], "level": "BEGINNER"}],
        },
    )
    client.post(
        "/api/job-descriptions",
        json={
            "user_id": company_admin["id"],
            "title": "JD Córdoba",
            "description": "Desc.",
            "province": "Córdoba",
            "required_skills": [{"skill_id": python_skill["id"], "level": "BEGINNER"}],
        },
    )

    response = client.get("/api/job-descriptions?province=Córdoba")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "JD Córdoba"


def test_delete_job_description(client, company_admin, python_skill):
    jd = client.post(
        "/api/job-descriptions",
        json={
            "user_id": company_admin["id"],
            "title": "JD a borrar",
            "description": "Desc.",
            "province": "Mendoza",
            "required_skills": [{"skill_id": python_skill["id"], "level": "PRO"}],
        },
    ).json()

    response = client.delete(f"/api/job-descriptions/{jd['id']}")
    assert response.status_code == 204

    response = client.delete(f"/api/job-descriptions/{jd['id']}")
    assert response.status_code == 404


def test_list_returns_empty_when_no_jobs(client):
    response = client.get("/api/job-descriptions")
    assert response.status_code == 200
    assert response.json() == []
```

---

## Task 7: Registrar job_descriptions en main.py

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Actualizar `app/main.py` completo**

Reemplazar el contenido del archivo con:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import settings
from app.database import SessionLocal, create_db_tables
from app.modules.attempts.router import router as attempts_router, student_attempts_router
from app.modules.gap_analysis.router import router as gap_analysis_router, student_gap_analyses_router
from app.modules.job_descriptions.router import router as job_descriptions_router
from app.modules.learning_paths.router import router as learning_paths_router, student_paths_router
from app.modules.skills.router import router as skills_router
from app.modules.skills.seed import seed_skills_if_empty
from app.modules.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    create_db_tables()
    db = SessionLocal()
    try:
        seed_skills_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, debug=settings.app_debug, lifespan=lifespan)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


app.include_router(users_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(job_descriptions_router, prefix="/api")
app.include_router(learning_paths_router, prefix="/api")
app.include_router(student_paths_router, prefix="/api")
app.include_router(attempts_router, prefix="/api")
app.include_router(student_attempts_router, prefix="/api")
app.include_router(gap_analysis_router, prefix="/api")
app.include_router(student_gap_analyses_router, prefix="/api")

_FRONTEND_DIR = Path("frontend/dist/public")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str) -> FileResponse:
    candidate = _FRONTEND_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(_FRONTEND_DIR / "index.html")
```

- [ ] **Step 2: Correr todos los tests**

```bash
pytest -v
```

Esperado: todos los tests pasan (skills + job_descriptions).

- [ ] **Step 3: Verificar que el servidor arranca sin errores**

```bash
uvicorn app.main:app --reload
```

Esperado: servidor corriendo en `http://localhost:8000`. Verificar `http://localhost:8000/api/health` devuelve `{"status": "ok", ...}` y `http://localhost:8000/docs` muestra los nuevos endpoints `/skills` y `/job-descriptions`.

---

## Task 8: Frontend — `api.ts` y constantes

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/constants.ts`

- [ ] **Step 1: Crear `frontend/src/lib/constants.ts`**

```typescript
import type { SkillLevel } from "./api";

export const ARGENTINIAN_PROVINCES: string[] = [
  "Buenos Aires",
  "CABA",
  "Catamarca",
  "Chaco",
  "Chubut",
  "Córdoba",
  "Corrientes",
  "Entre Ríos",
  "Formosa",
  "Jujuy",
  "La Pampa",
  "La Rioja",
  "Mendoza",
  "Misiones",
  "Neuquén",
  "Río Negro",
  "Salta",
  "San Juan",
  "San Luis",
  "Santa Cruz",
  "Santa Fe",
  "Santiago del Estero",
  "Tierra del Fuego",
  "Tucumán",
];

export const SKILL_LEVELS: SkillLevel[] = [
  "BEGINNER",
  "INTERMEDIATE",
  "ADVANCED",
  "PRO",
];

export const LEVEL_LABELS: Record<SkillLevel, string> = {
  BEGINNER: "Principiante",
  INTERMEDIATE: "Intermedio",
  ADVANCED: "Avanzado",
  PRO: "Pro",
};

export const LEVEL_COLORS: Record<SkillLevel, string> = {
  BEGINNER: "bg-gray-100 text-gray-700",
  INTERMEDIATE: "bg-blue-100 text-blue-700",
  ADVANCED: "bg-orange-100 text-orange-700",
  PRO: "bg-purple-100 text-purple-700",
};
```

- [ ] **Step 2: Agregar tipos y helpers a `frontend/src/lib/api.ts`**

Al final del archivo (antes del cierre), agregar:

```typescript
// ─── Skills ──────────────────────────────────────────────────────────────────

export interface Skill {
  id: number;
  name: string;
}

export const skills = {
  search: (q: string) =>
    request<Skill[]>(`/skills?q=${encodeURIComponent(q)}`),
  create: (name: string) =>
    request<Skill>("/skills", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
};

// ─── Job Descriptions ─────────────────────────────────────────────────────────

export type SkillLevel = "BEGINNER" | "INTERMEDIATE" | "ADVANCED" | "PRO";

export interface SkillRequirement {
  skill_id: number;
  skill_name: string;
  level: SkillLevel;
}

export interface PostedBy {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface JobDescription {
  id: number;
  title: string;
  description: string;
  province: string;
  posted_by: PostedBy;
  required_skills: SkillRequirement[];
  created_at: string;
}

export interface JobDescriptionCreate {
  user_id: number;
  title: string;
  description: string;
  province: string;
  required_skills: { skill_id: number; level: SkillLevel }[];
}

export const jobDescriptions = {
  list: (province?: string) =>
    request<JobDescription[]>(
      `/job-descriptions${province ? `?province=${encodeURIComponent(province)}` : ""}`,
    ),
  create: (data: JobDescriptionCreate) =>
    request<JobDescription>("/job-descriptions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    request<void>(`/job-descriptions/${id}`, { method: "DELETE" }),
};
```

---

## Task 9: Frontend — AppLayout rol empresa

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: Actualizar `AppLayout.tsx`**

Agregar `Briefcase` y `PlusCircle` al import de lucide-react:

```typescript
import { Bell, Briefcase, Home, BookOpen, GraduationCap, LineChart, MessageSquare, PlusCircle, Users, AlertCircle, FileText } from "lucide-react";
```

Actualizar la interface:

```typescript
interface AppLayoutProps {
  children: React.ReactNode;
  activePage: string;
  userRole?: "candidato" | "tutor" | "empresa";
  userName?: string;
}
```

Actualizar la función para incluir el rol empresa (justo después de donde se define `isCandidato`):

```typescript
export function AppLayout({ children, activePage, userRole = "candidato", userName = "Lucía Ramírez" }: AppLayoutProps) {
  const isCandidato = userRole === "candidato";
  const isEmpresa = userRole === "empresa";

  const candidatoLinks = [
    { name: "Inicio", path: "/", icon: Home },
    { name: "Mi Plan", path: "/plan", icon: BookOpen },
    { name: "Capacitación", path: "/modulo", icon: GraduationCap },
    { name: "Progreso", path: "/progreso", icon: LineChart },
    { name: "Mi Tutor", path: "/canal-tutor", icon: MessageSquare },
  ];

  const tutorLinks = [
    { name: "Mis Candidatos", path: "/panel-tutor", icon: Users },
    { name: "Alertas", path: "/panel-tutor", icon: AlertCircle },
    { name: "Reportes", path: "/panel-tutor", icon: FileText },
  ];

  const empresaLinks = [
    { name: "Puestos", path: "/jobs", icon: Briefcase },
    { name: "Nuevo Puesto", path: "/new-job", icon: PlusCircle },
  ];

  const links = isCandidato ? candidatoLinks : isEmpresa ? empresaLinks : tutorLinks;
  // ... (resto sin cambios)
```

También actualizar la condición del bloque "Tu Tutora" en el sidebar para que no aparezca en el rol empresa:

```typescript
{isCandidato && (
  <div className="p-4 mt-auto">
    {/* ... bloque Tu Tutora sin cambios ... */}
  </div>
)}
```

Este bloque ya usa `isCandidato`, por lo que la condición ya excluye empresa. Sin cambios necesarios aquí.

---

## Task 10: Frontend — Página `/new-job`

**Files:**
- Create: `frontend/src/pages/NuevoPuesto.tsx`

- [ ] **Step 1: Crear `frontend/src/pages/NuevoPuesto.tsx`**

```typescript
import React, { useCallback, useEffect, useState } from "react";
import { useLocation } from "wouter";
import { X } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { jobDescriptions, skills as skillsApi, Skill, SkillLevel } from "@/lib/api";
import {
  ARGENTINIAN_PROVINCES,
  LEVEL_COLORS,
  LEVEL_LABELS,
  SKILL_LEVELS,
} from "@/lib/constants";

// Hardcoded para MVP — reemplazar por user_id del token cuando se sume auth.
// Asegurate de que exista un usuario con este ID y rol company_admin en la BD.
const COMPANY_ADMIN_USER_ID = 1;

interface SelectedSkill {
  skill_id: number;
  skill_name: string;
  level: SkillLevel;
}

export function NuevoPuesto() {
  const [, navigate] = useLocation();
  const { toast } = useToast();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [province, setProvince] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<SelectedSkill[]>([]);
  const [skillQuery, setSkillQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Skill[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchSuggestions = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions([]);
      return;
    }
    const results = await skillsApi.search(q);
    setSuggestions(results);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchSuggestions(skillQuery), 300);
    return () => clearTimeout(timer);
  }, [skillQuery, fetchSuggestions]);

  const addSkill = async (skill: Skill | null, name?: string) => {
    let s = skill;
    if (!s && name) {
      s = await skillsApi.create(name);
    }
    if (!s) return;
    if (selectedSkills.some((sk) => sk.skill_id === s!.id)) return;
    setSelectedSkills((prev) => [
      ...prev,
      { skill_id: s!.id, skill_name: s!.name, level: "INTERMEDIATE" },
    ]);
    setSkillQuery("");
    setSuggestions([]);
  };

  const removeSkill = (skillId: number) => {
    setSelectedSkills((prev) => prev.filter((s) => s.skill_id !== skillId));
  };

  const updateLevel = (skillId: number, level: SkillLevel) => {
    setSelectedSkills((prev) =>
      prev.map((s) => (s.skill_id === skillId ? { ...s, level } : s)),
    );
  };

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim() || !province || selectedSkills.length === 0) {
      toast({ title: "Completá todos los campos", variant: "destructive" });
      return;
    }
    setIsSubmitting(true);
    try {
      await jobDescriptions.create({
        user_id: COMPANY_ADMIN_USER_ID,
        title: title.trim(),
        description: description.trim(),
        province,
        required_skills: selectedSkills.map((s) => ({
          skill_id: s.skill_id,
          level: s.level,
        })),
      });
      toast({ title: "Puesto publicado", description: "Tu oferta ya está disponible." });
      navigate("/jobs");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Error desconocido";
      toast({ title: "Error al publicar", description: message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const queryLower = skillQuery.toLowerCase();
  const canAddNew =
    skillQuery.trim().length > 0 &&
    !suggestions.some((s) => s.name.toLowerCase() === queryLower);

  return (
    <AppLayout activePage="Nuevo Puesto" userRole="empresa" userName="Empresa Global S.A.">
      <div className="max-w-2xl">
        <h2 className="text-xl font-bold mb-6">Publicar nuevo puesto</h2>

        <div className="space-y-5 bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
          {/* Título */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Título del puesto
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej: Backend Developer Senior"
            />
          </div>

          {/* Descripción */}
          <div>
            <label className="block text-sm font-medium mb-1">Descripción</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describí las responsabilidades, requisitos y condiciones del puesto..."
              rows={5}
            />
          </div>

          {/* Provincia */}
          <div>
            <label className="block text-sm font-medium mb-1">Provincia</label>
            <Select value={province} onValueChange={setProvince}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccioná una provincia" />
              </SelectTrigger>
              <SelectContent>
                {ARGENTINIAN_PROVINCES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Skills */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Skills requeridas
            </label>
            <div className="relative">
              <Input
                value={skillQuery}
                onChange={(e) => setSkillQuery(e.target.value)}
                placeholder="Buscá o escribí una skill y presioná Enter..."
                onKeyDown={(e) => {
                  if (e.key === "Enter" && skillQuery.trim()) {
                    e.preventDefault();
                    addSkill(null, skillQuery.trim());
                  }
                }}
              />
              {(suggestions.length > 0 || canAddNew) && (
                <div className="absolute z-10 w-full bg-white border border-slate-200 rounded-xl shadow-lg mt-1">
                  {suggestions.map((s) => (
                    <button
                      key={s.id}
                      className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 first:rounded-t-xl"
                      onClick={() => addSkill(s)}
                    >
                      {s.name}
                    </button>
                  ))}
                  {canAddNew && (
                    <button
                      className="w-full text-left px-4 py-2 text-sm text-[#4F46E5] hover:bg-indigo-50 last:rounded-b-xl border-t border-slate-100"
                      onClick={() => addSkill(null, skillQuery.trim())}
                    >
                      + Agregar &quot;{skillQuery}&quot;
                    </button>
                  )}
                </div>
              )}
            </div>

            {selectedSkills.length > 0 && (
              <div className="mt-3 space-y-2">
                {selectedSkills.map((sk) => (
                  <div
                    key={sk.skill_id}
                    className="flex items-center gap-2 flex-wrap"
                  >
                    <span className="font-medium text-sm w-28 shrink-0">
                      {sk.skill_name}
                    </span>
                    <div className="flex gap-1 flex-wrap">
                      {SKILL_LEVELS.map((l) => (
                        <button
                          key={l}
                          onClick={() => updateLevel(sk.skill_id, l)}
                          className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
                            sk.level === l
                              ? `${LEVEL_COLORS[l]} border-transparent`
                              : "bg-white border-slate-200 text-slate-500"
                          }`}
                        >
                          {LEVEL_LABELS[l]}
                        </button>
                      ))}
                    </div>
                    <button
                      onClick={() => removeSkill(sk.skill_id)}
                      className="text-slate-400 hover:text-red-400 ml-auto"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Button
            className="w-full bg-[#4F46E5] hover:bg-indigo-700"
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Publicando..." : "Publicar puesto"}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
```

---

## Task 11: Frontend — Página `/jobs` y rutas

**Files:**
- Create: `frontend/src/pages/ListadoPuestos.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Crear `frontend/src/pages/ListadoPuestos.tsx`**

```typescript
import { useState } from "react";
import { Link } from "wouter";
import { MapPin, Plus, User } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { jobDescriptions, JobDescription } from "@/lib/api";
import {
  ARGENTINIAN_PROVINCES,
  LEVEL_COLORS,
  LEVEL_LABELS,
} from "@/lib/constants";

export function ListadoPuestos() {
  const [province, setProvince] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["job-descriptions", province],
    queryFn: () => jobDescriptions.list(province || undefined),
  });

  return (
    <AppLayout activePage="Puestos" userRole="empresa" userName="Empresa Global S.A.">
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div className="w-64">
            <Select value={province} onValueChange={setProvince}>
              <SelectTrigger>
                <SelectValue placeholder="Todas las provincias" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todas las provincias</SelectItem>
                {ARGENTINIAN_PROVINCES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Link href="/new-job">
            <Button className="bg-[#4F46E5] hover:bg-indigo-700 flex items-center gap-2">
              <Plus className="w-4 h-4" /> Publicar puesto
            </Button>
          </Link>
        </div>

        {isLoading && (
          <div className="text-center text-slate-400 py-12">Cargando puestos...</div>
        )}

        {!isLoading && data?.length === 0 && (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-100">
            <p className="text-slate-500 text-lg font-medium">
              No hay puestos publicados
            </p>
            <p className="text-slate-400 text-sm mt-1">
              {province
                ? `No hay puestos en ${province}.`
                : "Publicá el primero."}
            </p>
            <Link href="/new-job">
              <Button className="mt-4 bg-[#4F46E5] hover:bg-indigo-700">
                Publicar el primero
              </Button>
            </Link>
          </div>
        )}

        {data && data.length > 0 && (
          <div className="space-y-4">
            {data.map((jd: JobDescription) => (
              <div
                key={jd.id}
                className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-lg font-bold text-[#1E293B]">{jd.title}</h3>
                  <span className="text-xs text-slate-400 shrink-0 ml-4">
                    {new Date(jd.created_at).toLocaleDateString("es-AR")}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm text-slate-500 mb-4">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" /> {jd.province}
                  </span>
                  <span className="flex items-center gap-1">
                    <User className="w-4 h-4" /> {jd.posted_by.first_name}{" "}
                    {jd.posted_by.last_name}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {jd.required_skills.map((skill) => (
                    <span
                      key={skill.skill_id}
                      className={`px-2 py-1 rounded-lg text-xs font-medium ${LEVEL_COLORS[skill.level]}`}
                    >
                      {skill.skill_name} · {LEVEL_LABELS[skill.level]}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 2: Actualizar `frontend/src/App.tsx`**

Agregar imports de las dos páginas nuevas:

```typescript
import { NuevoPuesto } from "@/pages/NuevoPuesto";
import { ListadoPuestos } from "@/pages/ListadoPuestos";
```

Agregar las rutas dentro del `<Switch>`, antes de `<Route component={NotFound} />`:

```typescript
<Route path="/new-job" component={NuevoPuesto} />
<Route path="/jobs" component={ListadoPuestos} />
```

- [ ] **Step 3: Verificar compilación del frontend**

```bash
cd /home/dev/capacitaya/frontend
npm run build
```

Esperado: build exitoso sin errores de TypeScript. Warnings son OK.

- [ ] **Step 4: Smoke test manual**

Levantar backend y frontend:

```bash
# Terminal 1
cd /home/dev/capacitaya && source .venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2
cd /home/dev/capacitaya/frontend && npm run dev
```

Luego:
1. Crear un company_admin: `POST http://localhost:8000/api/users` con `{"first_name": "Empresa", "last_name": "Global", "email": "empresa@test.com", "role": "company_admin"}`. Anotar el `id` devuelto.
2. Actualizar `COMPANY_ADMIN_USER_ID` en `NuevoPuesto.tsx` con ese `id` si es diferente de 1.
3. Navegar a `http://localhost:5173/new-job` — debe mostrar el formulario con AppLayout rol empresa.
4. Completar título, descripción, provincia, agregar una skill, publicar.
5. Debe redirigir a `/jobs` mostrando la JD creada.
6. Cambiar el filtro de provincia — debe filtrar correctamente.

---

## Notas de prerequisito

**company_admin para el frontend:** La página `/new-job` usa `COMPANY_ADMIN_USER_ID = 1` hardcodeado. Para que funcione, debe existir en la BD un usuario con ese `id` y `role: "company_admin"`. Crearlo con:

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Empresa", "last_name": "Global", "email": "empresa@test.com", "role": "company_admin"}'
```

Si la BD ya tiene usuarios, el id asignado puede ser diferente de 1. Actualizar la constante en `NuevoPuesto.tsx`.
