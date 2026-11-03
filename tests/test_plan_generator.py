"""Tests del generador de planes: mock determinístico, base LLM y factory."""

from app.modules.learning_paths.plan_generator._base_llm import LlmBackedPlanGenerator
from app.modules.learning_paths.plan_generator.factory import (
    _PlanGeneratorWithMockFallback,
    get_plan_generator,
)
from app.modules.learning_paths.plan_generator.mock import MockPlanGenerator
from app.modules.learning_paths.schemas import LearningPhase


def test_mock_plan_skips_ready_and_orders_by_priority(gap_report):
    plan = MockPlanGenerator().generate(gap_report)
    # HTML está READY → se ignora; quedan Git (HIGH) y Python (LOW), en ese orden.
    assert [m.skill_name for m in plan.modules] == ["Git", "Python"]
    assert plan.generator_used == "mock"
    assert plan.readiness_score_initial == 40
    assert plan.student_email == "ana@example.com"


def test_mock_plan_unit_structure(gap_report):
    plan = MockPlanGenerator().generate(gap_report)
    module = plan.modules[0]
    assert [u.phase for u in module.units] == [
        LearningPhase.PASION, LearningPhase.PLAY, LearningPhase.PRACTICA,
    ]
    practica = module.units[2]
    assert len(practica.exercises) == 2
    # 2 módulos * (10+15+30) min = 110 min => 1.83 h
    assert plan.estimated_total_hours == round(110 / 60, 2)


class _FakeLlmClient:
    def generate_json(self, prompt, response_schema, temperature=0.7):
        return {
            "phase": "pasion",
            "title": "Título",
            "content": "Contenido de la unidad",
            "estimated_minutes": 1,
            "exercises": [
                {"prompt": "p", "type": "text", "expected_answer": "a", "difficulty": 2}
            ],
        }


def test_llm_backed_generator_builds_plan(gap_report):
    gen = LlmBackedPlanGenerator(_FakeLlmClient())
    gen.generator_name = "fake"
    plan = gen.generate(gap_report)
    assert [m.skill_name for m in plan.modules] == ["Git", "Python"]
    assert plan.generator_used == "fake"
    # Cada módulo tiene las 3 fases, con phase corregida por el generador.
    phases = [u.phase for u in plan.modules[0].units]
    assert phases == [LearningPhase.PASION, LearningPhase.PLAY, LearningPhase.PRACTICA]


def test_factory_returns_mock_for_mock_setting(monkeypatch):
    from app.modules.learning_paths.plan_generator import factory
    monkeypatch.setattr(factory.settings, "plan_generator", "mock")
    assert isinstance(get_plan_generator(), MockPlanGenerator)


def test_fallback_wrapper_uses_fallback_on_error(gap_report):
    class _Boom:
        def generate(self, gap_report):
            raise RuntimeError("primary down")

    wrapped = _PlanGeneratorWithMockFallback(_Boom(), MockPlanGenerator())
    plan = wrapped.generate(gap_report)
    assert plan.generator_used == "mock"
