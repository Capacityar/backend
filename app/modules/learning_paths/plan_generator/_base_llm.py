import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Protocol

from pydantic import ValidationError

from app.config import settings
from app.modules.learning_paths.plan_generator.prompts import build_unit_prompt
from app.modules.learning_paths.schemas import (
    GapReport,
    GapSkill,
    GeneratedModule,
    GeneratedPlan,
    GeneratedUnit,
    LearningPhase,
    SkillStatus,
)
from app.shared.llm import LlmTimeoutError


logger = logging.getLogger(__name__)

_PRIORITY_WEIGHT = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
_UNIT_PHASES = (LearningPhase.PASION, LearningPhase.PLAY, LearningPhase.PRACTICA)
_PHASE_MINUTES = {
    LearningPhase.PASION: 10,
    LearningPhase.PLAY: 15,
    LearningPhase.PRACTICA: 30,
}
_MAX_PARALLEL_CALLS = 5

UNIT_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "phase": {"type": "string", "enum": ["pasion", "play", "practica"]},
        "title": {"type": "string"},
        "content": {"type": "string"},
        "estimated_minutes": {"type": "integer"},
        "exercises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["multiple_choice", "text", "code"],
                    },
                    "expected_answer": {"type": "string"},
                    "difficulty": {"type": "integer"},
                },
                "required": ["prompt", "type", "expected_answer", "difficulty"],
            },
        },
    },
    "required": ["phase", "title", "content", "estimated_minutes", "exercises"],
}


class _LlmClient(Protocol):
    def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.7,
    ) -> dict[str, Any]: ...


class LlmBackedPlanGenerator:
    """
    Build a learning plan whose structure is deterministic but whose unit
    content is produced by an LLM. Subclasses only need to inject a client
    and identify themselves via `generator_name`.
    """

    generator_name: str = "llm"

    def __init__(self, client: _LlmClient) -> None:
        self._client = client

    def generate(self, gap_report: GapReport) -> GeneratedPlan:
        skills_to_train = sorted(
            (s for s in gap_report.skills if s.status != SkillStatus.READY),
            key=lambda s: _PRIORITY_WEIGHT[s.priority.value],
        )

        unit_jobs = [
            (skill_index, skill, phase)
            for skill_index, skill in enumerate(skills_to_train)
            for phase in _UNIT_PHASES
        ]

        timeout = settings.llm_timeout_seconds
        executor = ThreadPoolExecutor(max_workers=_MAX_PARALLEL_CALLS)
        try:
            generated_units = list(
                executor.map(
                    lambda job: self._generate_unit(job[1], job[2], gap_report),
                    unit_jobs,
                    timeout=timeout,
                )
            )
        except TimeoutError as exc:
            logger.warning(
                "Plan generation with '%s' timed out after %ss.",
                self.generator_name,
                timeout,
            )
            raise LlmTimeoutError(
                f"Plan generation with '{self.generator_name}' timed out after {timeout}s"
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        modules: list[GeneratedModule] = []
        for skill_index, skill in enumerate(skills_to_train):
            units_for_skill = [
                generated_units[i]
                for i, job in enumerate(unit_jobs)
                if job[0] == skill_index
            ]
            modules.append(
                GeneratedModule(
                    skill_name=skill.name,
                    priority=skill.priority,
                    order_index=skill_index,
                    units=units_for_skill,
                )
            )

        total_minutes = sum(u.estimated_minutes for m in modules for u in m.units)

        return GeneratedPlan(
            student_email=gap_report.student.email,
            student_name=gap_report.student.name,
            company_name=gap_report.company.name,
            target_role_title=gap_report.target_role.title,
            gap_analysis_id=gap_report.id,
            readiness_score_initial=gap_report.readiness_score,
            modules=modules,
            estimated_total_hours=round(total_minutes / 60, 2),
            generator_used=self.generator_name,
        )

    def _generate_unit(
        self, skill: GapSkill, phase: LearningPhase, gap_report: GapReport
    ) -> GeneratedUnit:
        prompt = build_unit_prompt(skill, phase, gap_report)
        raw = self._client.generate_json(prompt, UNIT_RESPONSE_SCHEMA)
        raw["phase"] = phase.value
        raw["estimated_minutes"] = _PHASE_MINUTES[phase]
        raw.setdefault("exercises", [])
        try:
            unit = GeneratedUnit.model_validate(raw)
        except ValidationError as exc:
            logger.warning(
                "%s returned an invalid unit for skill=%s phase=%s: %s",
                self.generator_name,
                skill.name,
                phase.value,
                exc,
            )
            raise
        if unit.phase != phase:
            unit = unit.model_copy(update={"phase": phase})
        return unit
