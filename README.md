# Capacityar — Backend API

API REST de Capacityar, plataforma de análisis de brecha de habilidades.

Backend del proyecto Capacityar. El frontend está en [Capacityar/frontend](https://github.com/Capacityar/frontend).

**Stack:** Python 3.12 + FastAPI + SQLAlchemy + PostgreSQL/Neon + Docker

**Características:**
- Arquitectura modular por capacidad de negocio (router/service/repository)
- Endpoints RESTful con documentación Swagger/OpenAPI
- Integración con IA (Groq Llama + Gemini + fallback mock)
- PostgreSQL serverless con Neon + SQLite para desarrollo local
- Autenticación mock + JWT (Sprint 2)
- Migraciones con Alembic y CI con tests (cobertura >= 70%)
- Deploy automatizado en Render con Docker

## Documentación

- [Informe técnico](https://github.com/Capacityar/.github/blob/main/docs/informe-tecnico.md)
- [Stack tecnológico](https://github.com/Capacityar/.github/blob/main/docs/tech-stack.md)
- [Onboarding backend](docs/backend-onboarding.md)
- [Integración con IA](docs/ai-integration.md)

---
