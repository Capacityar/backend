"""Tests del feedback empático (Paciencia del modelo 5P), en modo mock/estático."""

from app.modules.attempts import feedback


def test_success_feedback_includes_name_skill_and_mastery():
    msg = feedback.generate_feedback(
        student_name="Ana", skill_name="Git", exercise_prompt="p",
        student_answer="a", expected_answer="a", is_correct=True, skill_mastery=0.5,
    )
    assert "Ana" in msg and "Git" in msg and "50%" in msg


def test_success_feedback_defaults_name():
    assert "estudiante" in feedback._success_feedback(None, "Git", 0.0)


def test_failure_feedback_static_in_mock_mode(monkeypatch):
    monkeypatch.setattr(feedback.settings, "plan_generator", "mock")
    msg = feedback.generate_feedback(
        student_name="Ana", skill_name="Git", exercise_prompt="p",
        student_answer="mal", expected_answer="bien", is_correct=False, skill_mastery=0.2,
    )
    assert msg == feedback._STATIC_FAILURE_MESSAGE
