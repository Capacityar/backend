import logging
from pathlib import Path
import time
from typing import Any
from unittest.mock import MagicMock

from fastapi import status
from fastapi.testclient import TestClient
import httpx
import pytest

from app.config import settings
from app.main import app as fastapi_app
from app.modules.attempts.feedback import (
    _STATIC_FAILURE_MESSAGE,
    generate_feedback,
)
from app.modules.learning_paths.plan_generator.factory import (
    _PlanGeneratorWithMockFallback,
    get_plan_generator,
)
from app.modules.learning_paths.plan_generator.groq import GroqPlanGenerator
from app.modules.learning_paths.plan_generator.mock import MockPlanGenerator
from app.modules.learning_paths.schemas import GapReport
from app.modules.resources import suggester
from app.shared import llm
from app.shared.llm import GeminiClient, GroqClient, LlmTimeoutError


def _sample_gap_report_dict(
    student_email: str = "timeout_student@example.com",
) -> dict[str, Any]:
    return {
        "student": {
            "name": "Lucia Perez",
            "email": student_email,
            "skills": [{"name": "Python", "level": 1}],
            "interests": ["musica", "tecnologia"],
        },
        "company": {"name": "Inclusión Tech"},
        "target_role": {
            "title": "Python Backend Trainee",
            "required_skills": [
                {"name": "Python", "level": 2, "priority": "HIGH"},
                {"name": "SQL", "level": 2, "priority": "MEDIUM"},
            ],
        },
        "summary": "Lucia requiere nivelar Python y SQL.",
        "readiness_score": 50,
        "skills": [
            {
                "name": "Python",
                "current_level": 1,
                "required_level": 2,
                "gap_level": 1,
                "priority": "HIGH",
                "status": "NEEDS_WORK",
            },
            {
                "name": "SQL",
                "current_level": 0,
                "required_level": 2,
                "gap_level": 2,
                "priority": "MEDIUM",
                "status": "MISSING",
            },
        ],
    }


class _SlowLlmClient:
    """Fake LLM client that sleeps longer than the configured timeout."""

    def __init__(self, delay_seconds: float = 0.5) -> None:
        self.delay_seconds = delay_seconds
        self.calls = 0

    def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        self.calls += 1
        time.sleep(self.delay_seconds)
        return {
            "phase": "pasion",
            "title": "Slow unit",
            "content": "Should have timed out before returning.",
            "estimated_minutes": 10,
            "exercises": [],
        }


def test_settings_has_llm_timeout_seconds() -> None:
    assert settings.llm_timeout_seconds == 30.0
    env_example = (
        Path(__file__).resolve().parent.parent / ".env.example"
    ).read_text(encoding="utf-8")
    assert "LLM_TIMEOUT_SECONDS=30.0" in env_example


def test_groq_client_passes_timeout_and_raises_llm_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_init: dict[str, Any] = {}
    captured_call: dict[str, Any] = {}

    class FakeGroqSdk:
        def __init__(self, **kwargs: Any) -> None:
            captured_init.update(kwargs)
            self.chat = MagicMock()
            self.chat.completions.create.side_effect = self._create

        def _create(self, **kwargs: Any) -> Any:
            captured_call.update(kwargs)
            raise httpx.ReadTimeout("Groq read timed out")

    monkeypatch.setattr(llm, "Groq", FakeGroqSdk)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 12.5)

    client = GroqClient(api_key="test-groq-key")
    assert captured_init["timeout"] == 12.5

    with pytest.raises(LlmTimeoutError) as exc_info:
        client.generate_json("prompt de prueba", {"type": "object"})

    assert captured_call["timeout"] == 12.5
    assert isinstance(exc_info.value, TimeoutError)
    assert "12.5s" in str(exc_info.value)


def test_gemini_client_passes_timeout_and_raises_llm_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_call: dict[str, Any] = {}

    class DeadlineExceeded(Exception):
        pass

    class FakeGenerativeModel:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def generate_content(self, prompt: str, **kwargs: Any) -> Any:
            captured_call["prompt"] = prompt
            captured_call.update(kwargs)
            raise DeadlineExceeded("504 Deadline Exceeded")

    monkeypatch.setattr(llm.genai, "configure", lambda **kwargs: None)
    monkeypatch.setattr(llm.genai, "GenerativeModel", FakeGenerativeModel)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 15.0)

    client = GeminiClient(api_key="test-gemini-key")

    with pytest.raises(LlmTimeoutError) as exc_info:
        client.generate_json("prompt gemini", {"type": "object"})

    assert captured_call["request_options"] == {"timeout": 15.0}
    assert isinstance(exc_info.value, TimeoutError)
    assert "15.0s" in str(exc_info.value)


def test_slow_client_triggers_timeout_and_mock_fallback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(settings, "llm_timeout_seconds", 0.05)

    slow_client = _SlowLlmClient(delay_seconds=0.5)
    primary = GroqPlanGenerator(client=slow_client)  # type: ignore[arg-type]
    generator = _PlanGeneratorWithMockFallback(primary, MockPlanGenerator())
    gap_report = GapReport.model_validate(_sample_gap_report_dict())

    with caplog.at_level(logging.WARNING):
        start = time.perf_counter()
        plan = generator.generate(gap_report)
        elapsed = time.perf_counter() - start

    # Must return promptly after the 0.05s timeout without waiting for the 0.5s sleep
    assert elapsed < 0.35
    assert plan.generator_used == "mock"
    assert len(plan.modules) == 2
    assert any(
        "timed out" in record.getMessage().lower() for record in caplog.records
    )


def test_create_learning_path_endpoint_degrades_to_mock_on_timeout(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(settings, "plan_generator", "groq")
    monkeypatch.setattr(settings, "llm_timeout_seconds", 0.05)

    slow_client = _SlowLlmClient(delay_seconds=0.5)
    fallback_generator = _PlanGeneratorWithMockFallback(
        GroqPlanGenerator(client=slow_client),  # type: ignore[arg-type]
        MockPlanGenerator(),
    )
    fastapi_app.dependency_overrides[get_plan_generator] = (
        lambda: fallback_generator
    )

    payload = _sample_gap_report_dict(
        student_email="endpoint_timeout@example.com"
    )

    with caplog.at_level(logging.WARNING):
        start = time.perf_counter()
        response = client.post("/api/learning-paths", json=payload)
        elapsed = time.perf_counter() - start

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["generator_used"] == "mock"
    assert data["student_email"] == "endpoint_timeout@example.com"
    assert len(data["modules"]) == 2
    # Also verifies _enrich_with_resources did not trigger 6 extra LLM timeouts
    assert elapsed < 0.45
    assert any(
        "falling back to mockplangenerator" in record.getMessage().lower()
        for record in caplog.records
    )


def test_resources_and_feedback_degrade_gracefully_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class TimeoutRaisingClient:
        def generate_json(
            self,
            prompt: str,
            response_schema: dict[str, Any],
            temperature: float = 0.7,
        ) -> dict[str, Any]:
            raise LlmTimeoutError("Simulated LLM timeout")

    monkeypatch.setattr(settings, "plan_generator", "groq")
    monkeypatch.setattr(settings, "llm_timeout_seconds", 5.0)
    monkeypatch.setattr(
        suggester, "_build_client", lambda: TimeoutRaisingClient()
    )
    monkeypatch.setattr(
        "app.modules.attempts.feedback._build_feedback_client",
        lambda: TimeoutRaisingClient(),
    )

    with caplog.at_level(logging.WARNING):
        resources = suggester.suggest_resources("Python", "pasion")
        feedback_msg = generate_feedback(
            student_name="Lucia",
            skill_name="Python",
            exercise_prompt="¿Qué es una lista en Python?",
            student_answer="Un entero",
            expected_answer="Una colección mutable ordenada",
            is_correct=False,
            skill_mastery=0.25,
        )

    assert resources == []
    assert feedback_msg == _STATIC_FAILURE_MESSAGE
    messages = [r.getMessage().lower() for r in caplog.records]
    assert any("resource suggestion timed out" in m for m in messages)
    assert any("llm timed out" in m and "feedback" in m for m in messages)
