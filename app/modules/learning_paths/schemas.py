from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.resources.schemas import ResourceView


# Entrada: GapReport del Equipo 1.
# El formato sigue lo definido en https://github.com/Capacityar/.github/blob/main/docs/gap-engine-mvp.md.


class SkillPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SkillStatus(str, Enum):
    READY = "READY"
    NEEDS_WORK = "NEEDS_WORK"
    MISSING = "MISSING"


class StudentSkill(BaseModel):
    name: str = Field(min_length=1)
    level: int = Field(ge=0, le=5)


class RequiredSkill(BaseModel):
    name: str = Field(min_length=1)
    level: int = Field(ge=0, le=5)
    priority: SkillPriority


class StudentInput(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    skills: list[StudentSkill] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class CompanyInput(BaseModel):
    name: str = Field(min_length=1)


class TargetRoleInput(BaseModel):
    title: str = Field(min_length=1)
    required_skills: list[RequiredSkill] = Field(min_length=1)


class GapSkill(BaseModel):
    name: str = Field(min_length=1)
    current_level: int = Field(ge=0, le=5)
    required_level: int = Field(ge=0, le=5)
    gap_level: int
    priority: SkillPriority
    status: SkillStatus


class GapReport(BaseModel):
    id: int | None = None
    student: StudentInput
    company: CompanyInput
    target_role: TargetRoleInput
    summary: str
    readiness_score: int = Field(ge=0, le=100)
    skills: list[GapSkill] = Field(min_length=1)
    created_at: datetime | None = None


# Salida: el plan generado por el PlanGenerator.


class LearningPhase(str, Enum):
    PASION = "pasion"
    PLAY = "play"
    PRACTICA = "practica"


class ExerciseType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    CODE = "code"


class GeneratedExercise(BaseModel):
    prompt: str
    type: ExerciseType
    expected_answer: str
    difficulty: int = Field(ge=1, le=5)


class GeneratedUnit(BaseModel):
    phase: LearningPhase
    title: str
    content: str
    estimated_minutes: int = Field(ge=1)
    exercises: list[GeneratedExercise] = Field(default_factory=list)
    resources: list[ResourceView] = Field(default_factory=list)


class GeneratedModule(BaseModel):
    skill_name: str
    priority: SkillPriority
    order_index: int = Field(ge=0)
    units: list[GeneratedUnit]


class GeneratedPlan(BaseModel):
    student_email: EmailStr
    student_name: str
    company_name: str
    target_role_title: str
    gap_analysis_id: int | None = None
    readiness_score_initial: int = Field(ge=0, le=100)
    modules: list[GeneratedModule]
    estimated_total_hours: float = Field(ge=0)
    generator_used: str

    model_config = ConfigDict(from_attributes=True)


# Persistencia: plan ya guardado con id y timestamps.


class PathStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class StoredLearningPath(GeneratedPlan):
    id: int
    status: PathStatus
    created_at: datetime
    updated_at: datetime
