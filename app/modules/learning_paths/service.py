from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.learning_paths.plan_generator.base import PlanGenerator
from app.modules.learning_paths.repository.base import LearningPathRepository
from app.modules.learning_paths.schemas import (
    GapReport,
    GeneratedPlan,
    SkillStatus,
    StoredLearningPath,
)
from app.modules.resources import service as resources_service
from app.modules.resources.schemas import ResourceView


def create_learning_path(
    generator: PlanGenerator,
    repository: LearningPathRepository,
    gap_report: GapReport,
    db: Session,
) -> StoredLearningPath:
    if all(s.status == SkillStatus.READY for s in gap_report.skills):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El estudiante ya cumple todos los requerimientos del puesto.",
        )
    plan = generator.generate(gap_report)
    plan = _enrich_with_resources(plan, db)
    return repository.save(plan)


def _enrich_with_resources(plan: GeneratedPlan, db: Session) -> GeneratedPlan:
    allow_llm = plan.generator_used != "mock"
    for module in plan.modules:
        for unit in module.units:
            stored = resources_service.get_or_suggest(
                db, module.skill_name, unit.phase.value, allow_llm=allow_llm
            )
            unit.resources = [ResourceView.model_validate(r) for r in stored]
    return plan


def get_learning_path(
    repository: LearningPathRepository, path_id: int
) -> StoredLearningPath:
    path = repository.find_by_id(path_id)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path no encontrado.",
        )
    return path


def list_learning_paths(
    repository: LearningPathRepository, offset: int = 0, limit: int = 100
) -> list[StoredLearningPath]:
    return repository.list_all(offset=offset, limit=limit)


def list_paths_by_student(
    repository: LearningPathRepository, email: str
) -> list[StoredLearningPath]:
    return repository.find_by_student_email(email)
