# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Capacity AR API: MVP backend para una plataforma de aprendizaje adaptativo (5P + ITS con tutoría humana). El sistema se divide en dos equipos sobre el **mismo monolito modular** — Equipo 1 produce `GapReport`, Equipo 2 (este repo, módulos principales `learning_paths`, `attempts`, `resources`) lo consume y produce un plan pedagógico que el alumno luego ejecuta. Ver [docs/scope-equipos.md](https://github.com/Capacityar/.github/blob/main/docs/scope-equipos.md) para el contrato entre equipos.

Stack: Python 3.12, FastAPI, SQLAlchemy 2.x síncrono, PostgreSQL en producción (Render + Neon), SQLite válido para desarrollo local. IA generativa vía Groq (default) o Google Gemini.

## Comandos

```bash
# Entorno
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Levantar API (autoreload)
uvicorn app.main:app --reload
# Swagger: http://localhost:8000/docs

# Tests (pytest configurado en pyproject.toml, testpaths=["tests"])
# Nota: el directorio tests/ todavía no existe — al agregarlo, instalar dev deps:
pip install -e ".[dev]"
pytest                              # toda la suite
pytest tests/path/to/test_file.py   # un archivo
pytest -k "nombre_del_test"         # filtrar por nombre
```

Para correr con SQLite (sin PostgreSQL local), poner en `.env`:
```
DATABASE_URL=sqlite:///./capacity_ar_local.db
```

## Despliegue

- **Producción**: Render (Web Service free tier) + Neon (PostgreSQL serverless free tier).
- Auto-deploy desde la branch `main` por webhook de GitHub. Cada push dispara build + redeploy.
- Variables de entorno cargadas en Render → Environment (no en `render.yaml`).
- URL pública: `https://capacity-ar-ap.onrender.com`.

## Arquitectura

### Patrón de módulo (estricto, replicar al agregar capacidades)

Cada módulo en `app/modules/<capability>/` sigue capas con responsabilidad única:

- `router.py` — endpoints HTTP, validación de payloads, dependencias FastAPI. Sin reglas de negocio.
- `service.py` — orquestación, reglas, decisiones de error (HTTPException). Sin SQLAlchemy.
- `repository.py` — único lugar con SQLAlchemy. Funciones puras sobre `Session`.
- `models.py` — modelos SQLAlchemy declarativos (heredan de `app.database.Base`).
- `schemas.py` — contratos Pydantic de entrada/salida.

**Regla:** los routers NO importan SQLAlchemy directamente. Los services NO arman queries. El repositorio NO levanta HTTPException. Esta separación está validada en `docs/backend-onboarding.md` y es la convención que el código existente respeta.

### Módulos implementados

| Módulo | Endpoints | Persistencia |
|---|---|---|
| `users` | CRUD `/users` | Postgres |
| `learning_paths` | `POST/GET /learning-paths`, `GET /students/{email}/learning-paths` | Postgres (plan completo como JSON) |
| `attempts` | `POST/GET /attempts`, `GET /students/{email}/attempts` | Postgres |
| `resources` | (sin endpoints todavía) | Postgres |

### Inversión con Protocol + factory (módulo `learning_paths`)

`learning_paths` usa un patrón que se replica cuando hay proveedores externos:

- `plan_generator/base.py` define un `Protocol` (`PlanGenerator`).
- `plan_generator/_base_llm.py` clase base con la lógica común (paralelización, estructura del plan).
- `plan_generator/mock.py` — implementación determinística sin IA.
- `plan_generator/gemini.py` — Google Gemini.
- `plan_generator/groq.py` — Groq Llama (default actual).
- `plan_generator/factory.py` — lee env var `PLAN_GENERATOR` y elige. Envuelve los LLMs en `_PlanGeneratorWithMockFallback` para que la API nunca rompa por culpa del LLM.
- Mismo patrón en `repository/` (Protocol + implementación in-memory + SQLAlchemy + factory).

Para sumar un proveedor nuevo: crear `<Provider>Client` en `app/shared/llm.py` y `<Provider>PlanGenerator` (4 líneas) heredando de `LlmBackedPlanGenerator`. Cambiar el factory para reconocerlo. El resto del sistema no se entera.

### Integración con IA

Tres puntos del sistema usan el LLM activo (Groq o Gemini según `PLAN_GENERATOR`):

1. **Generación de units** en `learning_paths` — title, content y 5 ejercicios multiple_choice por unit.
2. **Sugerencia de recursos** en `resources/suggester.py` — videos, guías, sandboxes. Cacheados por `(skill, fase)` en BD para no repetir llamadas.
3. **Feedback empático** en `attempts/feedback.py` — Paciencia (4° P del modelo 5P) cuando un alumno falla un ejercicio.

Ver `docs/ai-integration.md` para detalles de la estrategia híbrida, manejo de fallas, y guardrails anti-alucinación de URLs.

### Bootstrap y persistencia

- `app/main.py` corre `create_db_tables()` en el `lifespan` startup. Esto invoca `Base.metadata.create_all` — válido sólo para MVP. Cuando empiece a haber cambios de schema con datos reales en ambientes persistentes, sumar Alembic.
- `app/config.py` normaliza URLs `postgres://` y `postgresql://` al driver `postgresql+psycopg://` (necesario porque Render/Neon entregan URLs sin el driver explícito).
- `app/database.py` expone `get_db` (generator usado como FastAPI dependency).
- **Pin de Python 3.12 obligatorio en Render**: el archivo `.python-version` con `3.12.7`. Sin él, Render usa Python 3.14 y SQLAlchemy 2.0.36 falla con `Mapped[int | None]`.

### Contratos entre equipos

El módulo `learning_paths` recibe un `GapReport` (definido en `app/modules/learning_paths/schemas.py`, alineado con [docs/gap-engine-mvp.md](https://github.com/Capacityar/.github/blob/main/docs/gap-engine-mvp.md)). Si el formato del GapReport cambia, **es un cambio de contrato entre equipos** — coordinar antes de tocar los schemas.

`SkillStatus` values: `READY`, `NEEDS_WORK`, `MISSING`. Si todas las skills llegan en `READY`, `create_learning_path` devuelve 409 (no genera plan vacío).

### Identificación de ejercicios (sin auth)

`attempts` usa **identificadores compuestos** en lugar de IDs propios:

```
learning_path_id + module_index + unit_index + exercise_index
```

El service abre el `plan_json` del path y busca el ejercicio en esa posición. Trade-off documentado en [docs/training-module-design.md](https://github.com/Capacityar/.github/blob/main/docs/training-module-design.md). Cuando se normalicen los exercises a tabla propia, este endpoint pasa a usar `exercise_id`.

### Roles y acceso

`UserRole`: `student | tutor | company_admin | admin`. La matriz completa de permisos por entidad está en [docs/access-matrix.md](https://github.com/Capacityar/.github/blob/main/docs/access-matrix.md). **Auth está diferida intencionalmente** (decisión documentada) — los endpoints son públicos en MVP. Cuando se sume `auth/`, los chequeos van como dependency, no cambia la matriz.

Regla de visibilidad relevante para diseñar nuevos endpoints:
- estudiante nunca ve su `readiness_score` numérico crudo ni sus alertas
- tutor sólo ve a sus asignados
- empresa en MVP **no ve avance** de estudiantes

### Cobertura del modelo 5P

Implementado: Pasión, Play, Práctica (en `prompts.py`), Paciencia (en `attempts/feedback.py`).
Pendiente: Perseverancia (módulos `student_metrics` y `alerts`).
Ver [docs/5p-coverage.md](https://github.com/Capacityar/.github/blob/main/docs/5p-coverage.md) para el mapeo detallado y por qué Paciencia/Perseverancia son transversales (no fases del plan).

## Convenciones específicas del proyecto

- Python 3.12, tipado estricto en firmas públicas (ver código existente como referencia).
- Versiones de dependencias **pinneadas exactas** en `requirements.txt` y `pyproject.toml`. No usar rangos.
- Comentarios y docs en español (sigue lo existente en `docs/` y en el código).
- `from_attributes=True` (Pydantic v2) cuando un schema mapea desde un modelo SQLAlchemy.
- **No referencias a Claude en commits ni en código** (preferencia explícita del autor).
- **No remover el fallback a Mock** del plan_generator. Si el LLM falla, el endpoint sigue funcionando con plan placeholder y `generator_used: "mock"`.
- **Anti-alucinación de URLs en `resources`**: para videos siempre usar search queries en YouTube (`https://www.youtube.com/results?search_query=...`). URLs canónicas solo para dominios whitelisteados en `suggester._KNOWN_DOC_DOMAINS`.

## Variables de entorno

`DATABASE_URL` (Postgres), `PLAN_GENERATOR` (`mock` / `groq` / `gemini`), `GROQ_API_KEY` + `GROQ_MODEL`, `GEMINI_API_KEY` + `GEMINI_MODEL`. Ver `docs/ai-integration.md` para detalles. Cambiar de proveedor en producción: editar `PLAN_GENERATOR` en Render → Environment, sin tocar código.
