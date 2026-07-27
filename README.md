# capacitaya — Backend API

API REST de capacityAr, plataforma IA de brecha de habilidades.

Backend del proyecto capacityAr. El frontend está en [etrigan16/capacityAr](https://github.com/etrigan16/capacityAr).

**Stack:** Python 3.12 + FastAPI + SQLAlchemy + PostgreSQL/Neon + Docker

**Rol en el proyecto:** Scrum Master (equipo de 13 personas, nota 10).

**Características:**
- Arquitectura modular por capacidad de negocio (router/service/repository)
- Endpoints RESTful con documentación Swagger/OpenAPI
- Integración con IA (Groq Llama + Gemini + fallback mock)
- PostgreSQL serverless con Neon + SQLite para desarrollo local
- Deploy automatizado en Render con Docker

---
