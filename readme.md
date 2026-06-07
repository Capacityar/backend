# CapacityAR Backend

API REST del Sistema de Tutoría Inteligente (ITS) con modelo pedagógico 5P y Human-in-the-Loop.

**Producción:** https://capacity-ar-ap.onrender.com  
**Swagger:** https://capacity-ar-ap.onrender.com/docs  
**Repos frontend:** https://github.com/Capacityar/frontend  
**Tablero:** https://github.com/orgs/Capacityar/projects/1

---

## Stack

- Python 3.12.7 + FastAPI 0.115.6 + Uvicorn 0.34.0
- SQLAlchemy 2.0.36 (síncrono) + Pydantic v2
- PostgreSQL 17 (Neon serverless, free tier)
- SQLite válido para desarrollo local
- Groq (Llama) + Google Gemini + Mock fallback
- Render (Web Service free tier, auto-deploy desde main)

## Arquitectura

Monolito modular en `app/modules/<capabilidad>/` con separación estricta de capas:

| Capa | Archivo | Responsabilidad |
|------|---------|----------------|
| Router | `router.py` | Endpoints HTTP, validación de payloads |
| Service | `service.py` | Reglas de negocio, orquestación, errores |
| Repository | `repository.py` | Único lugar con SQLAlchemy |
| Models | `models.py` | Modelos declarativos |
| Schemas | `schemas.py` | Contratos Pydantic |

Los proveedores externos (LLMs) se inyectan con patrón Protocol + Factory.

## Módulos implementados

| Módulo | Endpoints | Estado |
|--------|-----------|--------|
| users | CRUD /users | ✅ |
| skills | CRUD /skills + seed | ✅ |
| user_skills | /students/{email}/skills | ✅ |
| job_descriptions | CRUD /job-descriptions | ✅ |
| gap_analysis | upload + extracción + LIFO | ✅ |
| learning_paths | POST/GET /learning-paths | ✅ |
| attempts | POST/GET /attempts | ✅ |
| resources | (consumido internamente) | ✅ |

## Desarrollo local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
# http://localhost:8000/docs
```

Para usar SQLite (sin PostgreSQL local):
```
DATABASE_URL=sqlite:///./capacity_ar_local.db
```

## Variables de entorno

| Variable | Valores | Default |
|----------|---------|---------|
| DATABASE_URL | URL de conexión | sqlite:///./capacity_ar_local.db |
| PLAN_GENERATOR | mock / groq / gemini | groq |
| GROQ_API_KEY | API key de Groq | — |
| GROQ_MODEL | Modelo Groq | — |
| GEMINI_API_KEY | API key de Gemini | — |
| GEMINI_MODEL | Modelo Gemini | — |

## Documentación

- [Backlog completo](docs/backlog.md)
- [Informe técnico](docs/informe-tecnico.md)
- [Arquitectura backend](docs/backend-onboarding.md)
- [Integración con IA](docs/ai-integration.md)
- [Cobertura 5P](docs/5p-coverage.md)
- [Matriz de accesos](docs/access-matrix.md)
