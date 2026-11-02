# Changelog

Todos los cambios relevantes del backend se registran acá. El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones siguen la [política de versionado](docs/versioning.md).

## [0.5.0] — Línea base Sprint 1 (Gestión de configuración)

Primera línea base del proyecto. Congela el estado de `main` al cierre del Sprint 1. El tag `v0.5.0` se crea sobre `main` después de mergear este registro.

### Incluye

**Módulos de la API** (todos bajo el prefijo `/api`, documentados en `/docs` con Swagger):

| Módulo | Qué hace |
|--------|----------|
| `users` | Alta y gestión de usuarios con rol (`student`, `tutor`, `company_admin`, `admin`) |
| `skills` | Catálogo de habilidades, con datos iniciales |
| `user_skills` | Habilidades declaradas por cada alumno |
| `job_descriptions` | Descripciones de puestos |
| `gap_analysis` | Extracción de habilidades desde CV/puesto y cálculo de brecha |
| `learning_paths` | Plan de capacitación 5P generado con IA (Groq o Gemini, con respaldo a mock) |
| `attempts` | Intentos de ejercicios, mastery por skill y feedback empático (4ª P, Paciencia) |
| `resources` | Recursos de estudio sugeridos por IA, con filtro anti-alucinación de URLs |

**Infraestructura y configuración:**

- Deploy en Render (`render.yaml`) y base PostgreSQL en Neon.
- El backend ya no incluye el frontend: vive en `Capacityar/frontend` (PR #49).
- Migraciones de base de datos versionadas con Alembic, con migración inicial del esquema (#30).
- CORS configurado para el frontend (#29).
- `.env.example` con todas las variables que lee `app/config.py` (#22).
- Suite de tests de integración de la API con base en memoria (#32).

### Corregido

- `Dockerfile`: sintaxis del `CMD` (#20).
- `render.yaml`: indentación de `envVars` (#21).

### No incluido (pendiente para próximas versiones)

- Autenticación (#12).
- Integración continua con GitHub Actions (#33) y tests unitarios (#31), en revisión.
- Épicas funcionales 1 a 7 (métricas del alumno, tutores, alertas, next-unit, validaciones, eventos).
