import logging
from urllib.parse import quote_plus

from app.config import settings
from app.modules.resources.models import Resource
from app.shared.llm import GeminiClient, GroqClient, LlmConfigurationError


logger = logging.getLogger(__name__)


_PHASE_INSTRUCTIONS = {
    "pasion": (
        "Sugerí 2 recursos motivacionales: un video corto que despierte ganas de "
        "aprender la habilidad (preferentemente charla, historia de un dev real, "
        "demo inspiradora) y una lectura/articulo introductorio."
    ),
    "play": (
        "Sugerí 2 recursos para explorar la habilidad jugando: un sandbox o "
        "playground interactivo (preferentemente con UI visual, sin instalar nada) "
        "y un tutorial corto practico."
    ),
    "practica": (
        "Sugerí 3 recursos para practicar y consolidar: una guía oficial o "
        "documentación de referencia, un cheatsheet, y una plataforma con "
        "ejercicios reales (FreeCodeCamp, HackerRank, etc.)."
    ),
}

_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["video", "guide", "sandbox", "reading"],
                    },
                    "title": {"type": "string"},
                    "source": {"type": "string"},
                    "search_terms": {
                        "type": "string",
                        "description": (
                            "Terminos de busqueda en YouTube o Google si no hay URL canonica. "
                            "Si la URL canonica existe (MDN, docs oficiales), devolve cadena vacia."
                        ),
                    },
                    "canonical_url": {
                        "type": "string",
                        "description": (
                            "URL real solo si es estable (MDN, git-scm.com, docs.python.org, etc). "
                            "Si no estas seguro, dejala vacia y completa search_terms."
                        ),
                    },
                    "description": {"type": "string"},
                    "duration_minutes": {"type": "integer"},
                    "level": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                    },
                },
                "required": ["type", "title", "source", "description", "level"],
            },
        },
    },
    "required": ["resources"],
}


_KNOWN_DOC_DOMAINS = (
    "developer.mozilla.org",
    "docs.python.org",
    "git-scm.com",
    "react.dev",
    "reactjs.org",
    "nodejs.org",
    "freecodecamp.org",
    "w3schools.com",
    "tailwindcss.com",
    "djangoproject.com",
    "fastapi.tiangolo.com",
    "kotlinlang.org",
    "developer.android.com",
    "aws.amazon.com",
    "azure.microsoft.com",
    "cloud.google.com",
)


def _build_client():
    choice = settings.plan_generator.lower()
    if choice == "groq":
        return GroqClient()
    if choice == "gemini":
        return GeminiClient()
    raise LlmConfigurationError(
        f"PLAN_GENERATOR='{settings.plan_generator}' does not support resource suggestions."
    )


def _resolve_url(item: dict, skill_name: str) -> str:
    canonical = (item.get("canonical_url") or "").strip()
    if canonical and any(domain in canonical for domain in _KNOWN_DOC_DOMAINS):
        return canonical

    search_terms = (item.get("search_terms") or "").strip()
    query = search_terms or f"{skill_name} {item.get('title', '')}"
    item_type = item.get("type", "guide")

    if item_type == "video":
        return f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _mock_resources(skill_name: str, phase: str) -> list[Resource]:
    """Deterministic fallback used when no LLM client is configured (mock mode)."""
    base_query = quote_plus(skill_name)
    templates: dict[str, list[dict]] = {
        "pasion": [
            {
                "type": "video",
                "title": f"Introducción a {skill_name}",
                "url": f"https://www.youtube.com/results?search_query={quote_plus(skill_name + ' introduccion para principiantes')}",
            },
            {
                "type": "reading",
                "title": f"¿Qué es {skill_name}?",
                "url": f"https://www.google.com/search?q={base_query}+que+es",
            },
        ],
        "play": [
            {
                "type": "sandbox",
                "title": f"Playground de {skill_name}",
                "url": f"https://www.google.com/search?q={base_query}+playground+online",
            },
            {
                "type": "video",
                "title": f"Tutorial práctico de {skill_name}",
                "url": f"https://www.youtube.com/results?search_query={quote_plus(skill_name + ' tutorial practico')}",
            },
        ],
        "practica": [
            {
                "type": "guide",
                "title": f"Documentación de {skill_name}",
                "url": f"https://www.google.com/search?q={base_query}+documentacion+oficial",
            },
            {
                "type": "guide",
                "title": f"Ejercicios de {skill_name} en FreeCodeCamp",
                "url": f"https://www.google.com/search?q={quote_plus(skill_name + ' freecodecamp ejercicios')}",
            },
        ],
    }
    items = templates.get(phase, [])
    return [
        Resource(
            skill_name=skill_name,
            phase=phase,
            type=item["type"],
            title=item["title"],
            url=item["url"],
            description=None,
            duration_minutes=None,
            source="mock",
            language="es",
            level="beginner",
            generated_by="mock",
            is_active=True,
        )
        for item in items
    ]


def suggest_resources(
    skill_name: str,
    phase: str,
    language: str = "es",
    allow_llm: bool = True,
) -> list[Resource]:
    instructions = _PHASE_INSTRUCTIONS.get(phase)
    if instructions is None:
        return []

    if not allow_llm:
        logger.info(
            "LLM bypassed (plan degraded to mock) — using mock resources for skill=%s phase=%s",
            skill_name,
            phase,
        )
        return _mock_resources(skill_name, phase)

    try:
        client = _build_client()
    except LlmConfigurationError:
        logger.info(
            "No LLM client configured — using mock resources for skill=%s phase=%s",
            skill_name,
            phase,
        )
        return _mock_resources(skill_name, phase)

    prompt = f"""Sos un curador de contenido para una plataforma argentina de capacitacion IT
dirigida a jovenes principiantes. Tu tarea es sugerir recursos de aprendizaje en {language}
(o ingles si no hay material en {language}) para una habilidad concreta y una fase pedagogica.

Habilidad: {skill_name}
Fase: {phase}

{instructions}

Reglas estrictas para evitar links rotos:
- Si conoces una URL canonica de documentacion oficial estable (MDN, git-scm.com,
  docs.python.org, react.dev, freecodecamp.org, etc.), devolvela en canonical_url.
- Si NO estas seguro de una URL, dejala vacia y completa search_terms con los terminos
  de busqueda exactos para encontrarlo en YouTube (para videos) o Google (para texto).
- NUNCA inventes URLs de YouTube ni IDs de video.
- Prefiere canales/fuentes reconocidas: FreeCodeCamp, Traversy Media, The Net Ninja,
  Carlos Azaustre, Programacion ATS, MDN, Mozilla, Fazt, Midu, etc.

Devolve un JSON con la lista 'resources' segun el schema.
"""

    try:
        response = client.generate_json(prompt, _RESPONSE_SCHEMA, temperature=0.6)
    except TimeoutError:
        logger.warning(
            "Resource suggestion timed out after %ss for skill=%s phase=%s; returning empty list.",
            settings.llm_timeout_seconds,
            skill_name,
            phase,
        )
        return []
    except Exception:
        logger.exception(
            "Resource suggestion failed for skill=%s phase=%s", skill_name, phase
        )
        return []

    items = response.get("resources") or []
    if not isinstance(items, list):
        return []

    resources: list[Resource] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            resources.append(
                Resource(
                    skill_name=skill_name,
                    phase=phase,
                    type=item.get("type", "guide"),
                    title=item.get("title", "").strip()[:500] or skill_name,
                    url=_resolve_url(item, skill_name),
                    description=(item.get("description") or "").strip() or None,
                    duration_minutes=item.get("duration_minutes"),
                    source=(item.get("source") or "").strip() or None,
                    language=language,
                    level=item.get("level"),
                    generated_by=settings.plan_generator.lower(),
                    is_active=True,
                )
            )
        except Exception:
            logger.warning("Skipping malformed resource item: %r", item)
            continue
    return resources
