# Ingeniería de Requerimientos — Plataforma de Análisis de Brecha

**Versión 2.0 | Junio 2026**

**Proyecto:** CapacityAR — UMET Ingeniería de Software I

## Historial de Revisión

| Versión | Fecha | Descripción del Cambio |
|---------|-------|------------------------|
| 1.0 | Abril 2026 | Documento inicial basado en stack No-Code (n8n/Make) |
| 2.0 | Junio 2026 | Actualización completa: stack real, modelo 5P, épicas implementadas |

## 1. Introducción

### 1.1 Contexto

CapacityAR es un Sistema de Tutoría Inteligente (ITS) que capacita a jóvenes de barrios vulnerables de Argentina para insertarse en el sector IT. El sistema identifica brechas de habilidades, genera planes de capacitación personalizados con IA y acompaña al alumno con tutoría humana.

### 1.2 Stack real implementado

| Componente | Tecnología |
|------------|-----------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy |
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS |
| Base de datos | PostgreSQL 17 (Neon serverless) |
| IA | Groq (Llama) + Google Gemini + Mock fallback |
| Hosting | Render (Web Service free tier) |
| CI/CD | Auto-deploy desde main vía webhook GitHub |

**Nota:** El stack No-Code (n8n/Make) y OpenAI/Claude planteados en v1.0 fueron reemplazados por FastAPI/Python con Groq y Gemini como proveedores de IA.

## 2. Modelo Pedagógico

El sistema implementa el modelo de las **5P** con **Human-in-the-Loop (HITL)**:

| P | Implementación | Estado |
|---|----------------|--------|
| **Pasión** | Fase del plan generada por LLM conectando skill con empresa concreta | ✅ |
| **Play** | Micro-contenido + recursos externos (sandbox, video) | ✅ |
| **Práctica** | 5 ejercicios multiple_choice A/B/C/D por skill, umbral 80% | ✅ |
| **Paciencia** | Feedback empático vía LLM cuando el alumno falla, sin revelar respuesta | ✅ |
| **Perseverancia** | Módulos `sessions` + `student_metrics` — pendiente | ❌ |

## 3. Actores del Sistema

| Actor | Descripción | Implementado |
|-------|-------------|-------------|
| **Estudiante** | Joven que se capacita. Ve su plan, hace ejercicios, se comunica con tutor | ✅ |
| **Tutor** | Profesional que supervisa alumnos. Ve progreso, hace gap analysis | ✅ (frontend) / Pendiente (backend HITL) |
| **Empresa** | Publica puestos con skills requeridas | ✅ |
| **Admin** | Administra actores del sistema | ✅ |

## 4. Requerimientos Funcionales

### 4.1 Módulos implementados (C1–C6)

| RF | Descripción | Endpoints | Épica |
|----|-------------|-----------|-------|
| RF-01 | CRUD de usuarios con roles | `CRUD /users` + `GET /health` | C1 |
| RF-02 | Catálogo de habilidades IT | `CRUD /skills` + seed | C1 |
| RF-03 | Auto-reporte de skills del estudiante | `GET/POST /students/{email}/skills` | C1 |
| RF-04 | Gestión de puestos laborales | `CRUD /job-descriptions` | C1 |
| RF-05 | Upload y análisis de brecha por documentos | `POST /api/gap-analyses` (multipart) | C2 |
| RF-06 | Generación de plan de capacitación | `POST/GET /learning-paths` | C2 |
| RF-07 | Persistencia en PostgreSQL + deploy público | URL pública + auto-deploy | C3 |
| RF-08 | Generación de contenido con IA (Groq/Gemini) | Integrado en learning_paths | C4 |
| RF-09 | Registro de intentos de ejercicios | `POST/GET /attempts` | C5 |
| RF-10 | Feedback empático con IA | Integrado en attempts | C5 |
| RF-11 | Recursos externos por skill+fase con anti-alucinación | Integrado en learning_paths | C6 |

### 4.2 Módulos pendientes (Épicas 1–8)

| RF | Descripción | Esfuerzo | Épica |
|----|-------------|----------|-------|
| RF-12 | Sesiones y métricas de perseverancia | 3-4 h | E1 |
| RF-13 | CRUD de tutores y asignaciones (HITL) | 4-5 h | E2 |
| RF-14 | Alertas predictivas de abandono | 3-4 h | E3 |
| RF-15 | Next-unit logic y desbloqueo progresivo | 2-3 h | E4 |
| RF-16 | Validaciones con juicio humano | 3 h | E5 |
| RF-17 | Autenticación mock + JWT | 9-12 h | E6 |
| RF-18 | Eventos hacia Equipo 1 | 2 h | E7 |
| RF-19 | Tests, CORS, Alembic | 4-6 h | E8 |

### 4.3 Frontend — páginas implementadas

| Ruta | Componente | Descripción |
|------|-----------|-------------|
| `/` o `/login` | Login | Autenticación (mock) |
| `/student` | Dashboard | Dashboard del alumno |
| `/student/plan` | PlanCapacitacion | Plan de capacitación |
| `/student/modulo` | ModuloIA | Módulo de aprendizaje con IA |
| `/student/evaluacion` | Evaluacion | Ejercicios y evaluaciones |
| `/student/progreso` | ProgresoyLogros | Progreso y logros |
| `/student/canal-tutor` | CanalTutor | Comunicación con tutor |
| `/student/skills` | MisHabilidades | Perfil de habilidades |
| `/tutor` | PanelTutor | Panel del tutor |
| `/tutor/gap-analysis` | TutorGapAnalysis | Gap analysis |
| `/companies` | ListadoPuestos | Puestos de empresa |
| `/companies/new-job` | NuevoPuesto | Alta de puesto |

## 5. Requerimientos No Funcionales

| RNF | Descripción | Estado |
|-----|-------------|--------|
| RNF-01 | API pública en HTTPS | ✅ |
| RNF-02 | Persistencia en PostgreSQL serverless | ✅ |
| RNF-03 | Fallback automático a Mock si la IA falla | ✅ |
| RNF-04 | Anti-alucinación de URLs en recursos | ✅ |
| RNF-05 | Identificación por email (auth diferida) | ✅ |
| RNF-06 | Auto-deploy desde main | ✅ |
| RNF-07 | Tests automatizados | ❌ (Épica 8) |
| RNF-08 | Migraciones con Alembic | ❌ (Épica 8) |
| RNF-09 | CORS habilitado | ❌ (Épica 8) |

## 6. Arquitectura del Sistema

### 6.1 Patrón de módulo

```
app/modules/<capacidad>/
  router.py      — Endpoints HTTP
  service.py     — Reglas de negocio
  repository.py  — SQLAlchemy
  models.py      — Modelos declarativos
  schemas.py     — Pydantic
```

### 6.2 IA híbrida

El código determinístico fija la estructura del plan; el LLM solo rellena contenido. Tres puntos usan IA:
1. Generación de plan (learning_paths)
2. Recursos externos (resources/suggester.py)
3. Feedback empático (attempts/feedback.py)

### 6.3 División en equipos

- **Equipo 1 — Gap Engine:** Produce el GapReport (diagnóstico de brecha)
- **Equipo 2 — Capacitación + Tutores (este repo):** Consume GapReport, opera fases 1-4, supervisión humana

## 7. Matriz de Accesos

| Recurso | student | tutor | company_admin | admin |
|---------|---------|-------|--------------|-------|
| /users (propio) | R | R | R | CRUD |
| /users (otros) | — | — | — | CRUD |
| /learning-paths (propio) | R | R | — | R |
| /attempts (propio) | RW | R | — | R |
| /attempts (asignados) | — | R | — | R |
| /tutors/{id}/dashboard | — | R (propio) | — | R |
| /alerts | — | R (asignados) | — | R |
| /job-descriptions | — | R | CRUD | R |
| /students/{email}/progress | R (propio) | R (asignado) | — | R |
| /students/{email}/metrics | — | R (asignado) | — | R |

**Nota:** Auth diferida intencionalmente. Endpoints públicos en MVP (C1). Matriz lista para activar con `Depends(require_role(...))`.

## 8. Épicas y Esfuerzo

| Épica | Estado | Esfuerzo |
|-------|--------|----------|
| C1 — MVP backend + users | ✅ Completada | ~4 h |
| C2 — learning_paths | ✅ Completada | ~6 h |
| C3 — PostgreSQL + Render | ✅ Completada | ~5 h |
| C4 — IA Groq + Gemini | ✅ Completada | ~6 h |
| C5 — attempts + Paciencia | ✅ Completada | ~3 h |
| C6 — resources | ✅ Completada | ~3 h |
| E1 — Perseverancia | ⏳ Pendiente | 3-4 h |
| E2 — Tutores | ⏳ Pendiente | 4-5 h |
| E3 — Alertas | ⏳ Pendiente | 3-4 h |
| E4 — Next-unit | ⏳ Pendiente | 2-3 h |
| E5 — Validaciones | ⏳ Pendiente | 3 h |
| E6 — Auth | ⏳ Pendiente | 9-12 h |
| E7 — Eventos | ⏳ Pendiente | 2 h |
| E8 — Calidad técnica | ⏳ Pendiente | 4-6 h |

**Total completado:** ~27 h  
**Total estimado pendiente:** ~30-42 h

## 9. Brechas respecto a v1.0

| Aspecto v1.0 | Cambio v2.0 |
|-------------|-------------|
| Stack No-Code (n8n/Make) | FastAPI + Python |
| IA: OpenAI/Claude | Groq + Gemini + Mock |
| Frontend no definido | React 19 + Vite + TypeScript |
| Base de datos no definida | PostgreSQL (Neon) |
| Hosting no definido | Render |
| 3 equipos independientes | 2 equipos sobre monolito modular |
| Sin modelo pedagógico específico | Modelo 5P + HITL |
