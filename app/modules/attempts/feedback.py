import logging

from app.config import settings
from app.shared.llm import GeminiClient, GroqClient, LlmConfigurationError


logger = logging.getLogger(__name__)


def _build_feedback_client():
    choice = settings.plan_generator.lower()
    if choice == "groq":
        return GroqClient()
    if choice == "gemini":
        return GeminiClient()
    raise LlmConfigurationError(
        f"PLAN_GENERATOR='{settings.plan_generator}' does not support LLM feedback."
    )


_FEEDBACK_SCHEMA: dict = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
}

_STATIC_SUCCESS_MESSAGE = (
    "¡Muy bien! Respuesta correcta. Cada acierto te acerca al dominio de esta habilidad."
)
_STATIC_FAILURE_MESSAGE = (
    "No te preocupes, equivocarte es parte de aprender. "
    "Repasá el concepto y volvé a intentarlo. La mayoría de los desarrolladores "
    "necesitó más de un intento en este tipo de ejercicios."
)


def generate_feedback(
    *,
    student_name: str | None,
    skill_name: str,
    exercise_prompt: str,
    student_answer: str,
    expected_answer: str,
    is_correct: bool,
    skill_mastery: float,
) -> str:
    if is_correct:
        return _success_feedback(student_name, skill_name, skill_mastery)
    return _failure_feedback(
        student_name=student_name,
        skill_name=skill_name,
        exercise_prompt=exercise_prompt,
        student_answer=student_answer,
        expected_answer=expected_answer,
        skill_mastery=skill_mastery,
    )


def _success_feedback(
    student_name: str | None, skill_name: str, skill_mastery: float
) -> str:
    nombre = student_name or "estudiante"
    return (
        f"¡Muy bien, {nombre}! Respuesta correcta. "
        f"Llevás un {int(skill_mastery * 100)}% de dominio en {skill_name}."
    )


def _failure_feedback(
    *,
    student_name: str | None,
    skill_name: str,
    exercise_prompt: str,
    student_answer: str,
    expected_answer: str,
    skill_mastery: float,
) -> str:
    try:
        client = _build_feedback_client()
    except LlmConfigurationError:
        return _STATIC_FAILURE_MESSAGE

    nombre = student_name or "el estudiante"
    prompt = f"""Sos un coach pedagogico empatico en una plataforma argentina de capacitacion IT
para jovenes de barrios vulnerables. La fase activa del modelo 5P es PACIENCIA:
tu objetivo es normalizar el error, evitar que el estudiante se frustre y reconectarlo
con el aprendizaje. NO digas si la respuesta era correcta, NO reveles la respuesta esperada.

Estudiante: {nombre}
Habilidad: {skill_name}
Ejercicio: {exercise_prompt}
Respuesta del estudiante: {student_answer}
Dominio actual del estudiante en esta habilidad: {int(skill_mastery * 100)}%

Generá un mensaje breve (maximo 60 palabras, 2-3 frases), en espanol rioplatense,
en segunda persona, calido pero no condescendiente. Normalizá el error,
ofrecé una pista conceptual sin dar la respuesta, y motivá a intentar de nuevo.

Devolve un JSON con la clave 'message' conteniendo el mensaje generado.
"""
    try:
        response = client.generate_json(prompt, _FEEDBACK_SCHEMA, temperature=0.8)
        message = response.get("message", "").strip()
        return message or _STATIC_FAILURE_MESSAGE
    except TimeoutError:
        logger.warning(
            "LLM timed out after %ss generating failure feedback for skill=%s; using static.",
            settings.llm_timeout_seconds,
            skill_name,
        )
        return _STATIC_FAILURE_MESSAGE
    except Exception:
        logger.exception(
            "LLM failed to generate failure feedback for skill=%s; using static.",
            skill_name,
        )
        return _STATIC_FAILURE_MESSAGE
