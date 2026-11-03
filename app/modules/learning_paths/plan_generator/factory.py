import logging

from app.config import settings
from app.modules.learning_paths.plan_generator.base import PlanGenerator
from app.modules.learning_paths.plan_generator.mock import MockPlanGenerator
from app.modules.learning_paths.schemas import GapReport, GeneratedPlan


logger = logging.getLogger(__name__)


class _PlanGeneratorWithMockFallback:
    def __init__(self, primary: PlanGenerator, fallback: PlanGenerator) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate(self, gap_report: GapReport) -> GeneratedPlan:
        try:
            return self._primary.generate(gap_report)
        except TimeoutError:
            logger.warning(
                "Primary plan generator timed out after %ss; falling back to MockPlanGenerator.",
                settings.llm_timeout_seconds,
            )
            return self._fallback.generate(gap_report)
        except Exception:
            logger.exception(
                "Primary plan generator failed; falling back to MockPlanGenerator."
            )
            return self._fallback.generate(gap_report)


def get_plan_generator() -> PlanGenerator:
    choice = settings.plan_generator.lower()

    if choice == "groq":
        try:
            from app.modules.learning_paths.plan_generator.groq import (
                GroqPlanGenerator,
            )

            return _PlanGeneratorWithMockFallback(
                GroqPlanGenerator(), MockPlanGenerator()
            )
        except Exception:
            logger.exception(
                "Could not initialize GroqPlanGenerator; using MockPlanGenerator."
            )
            return MockPlanGenerator()

    if choice == "gemini":
        try:
            from app.modules.learning_paths.plan_generator.gemini import (
                GeminiPlanGenerator,
            )

            return _PlanGeneratorWithMockFallback(
                GeminiPlanGenerator(), MockPlanGenerator()
            )
        except Exception:
            logger.exception(
                "Could not initialize GeminiPlanGenerator; using MockPlanGenerator."
            )
            return MockPlanGenerator()

    return MockPlanGenerator()
