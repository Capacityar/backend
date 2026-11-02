# Diseño: Job Descriptions (Descripciones de Puestos)

**Fecha:** 2026-05-29  
**Estado:** Aprobado

## Resumen

Permite que usuarios con rol `company_admin` publiquen descripciones de puestos de trabajo con título, provincia argentina y lista de skills requeridas (cada una con nivel). Se exponen tres endpoints REST y dos páginas en el frontend.

---

## Backend

### Módulo `skills`

**Tabla:** `skills(id PK, name VARCHAR(200) UNIQUE, created_at)`

**Endpoints:**

- `GET /skills?q=<texto>` — busca skills cuyo nombre contenga el texto (ILIKE), devuelve hasta 20 resultados. Usado por el autocomplete del frontend.
- `POST /skills` — crea una skill si no existe; si ya existe devuelve la existente. Retorna 201 si es nueva, 200 si ya existía.

**Seed inicial:** ~70 skills IT comunes se insertan al startup si la tabla `skills` está vacía. La lista cubre: lenguajes (Python, JavaScript, TypeScript, Java, Go, Rust, C#, PHP, Ruby, Kotlin, Swift), frameworks web (React, Vue, Angular, Next.js, FastAPI, Django, Spring Boot, Laravel, Rails, Express, NestJS), bases de datos (PostgreSQL, MySQL, MongoDB, Redis, SQLite, Elasticsearch, DynamoDB), DevOps/infra (Docker, Kubernetes, AWS, GCP, Azure, Terraform, Ansible, CI/CD, GitHub Actions, Linux), datos/IA (SQL, Pandas, NumPy, TensorFlow, PyTorch, Scikit-learn, Spark, dbt, Airflow), y herramientas generales (Git, REST APIs, GraphQL, gRPC, Agile/Scrum, Jira, Figma).

**Patrón de módulo:** router → service → repository → models → schemas (igual que módulos existentes).

---

### Módulo `job_descriptions`

**Tablas:**

```
job_descriptions
  id            PK
  user_id       FK → users.id (NOT NULL)
  title         VARCHAR(300) NOT NULL
  description   TEXT NOT NULL
  province      VARCHAR(100) NOT NULL
  created_at    TIMESTAMP WITH TZ
  updated_at    TIMESTAMP WITH TZ

job_description_skills
  job_description_id  FK → job_descriptions.id (CASCADE DELETE)
  skill_id            FK → skills.id
  level               ENUM('BEGINNER','INTERMEDIATE','ADVANCED','PRO') NOT NULL
  PK: (job_description_id, skill_id)
```

**Endpoints:**

- `POST /job-descriptions`  
  Body: `{user_id: int, title: str, description: str, province: str, required_skills: [{skill_id: int, level: str}]}`  
  Valida que `user_id` exista y sea `company_admin`. Valida que `required_skills` tenga al menos 1 elemento. Devuelve la JD creada con skills expandidas. Status 201.

- `GET /job-descriptions?province=<provincia>`  
  Lista todas las JDs (o filtradas por provincia exacta). Incluye datos del usuario que publicó (`first_name`, `last_name`, `email`) y la lista de skills con nivel. Sin paginación. Ordenadas por `created_at DESC`.

- `DELETE /job-descriptions/{id}`  
  Borra la JD. Las filas en `job_description_skills` se eliminan en cascade. Status 204.

**Respuesta de JD (schema):**

```json
{
  "id": 1,
  "title": "Backend Developer Senior",
  "description": "Buscamos un backend developer con experiencia en...",
  "province": "Buenos Aires",
  "posted_by": {
    "id": 5,
    "first_name": "Empresa",
    "last_name": "Global",
    "email": "empresa@global.com"
  },
  "required_skills": [
    {"skill_id": 3, "skill_name": "Python", "level": "ADVANCED"},
    {"skill_id": 7, "skill_name": "Docker", "level": "INTERMEDIATE"}
  ],
  "created_at": "2026-05-29T12:00:00Z"
}
```

---

## Frontend

### Páginas nuevas

#### `/new-job` — Nueva descripción de puesto

Formulario con:
- **Título del puesto** — input de texto libre
- **Descripción** — textarea multiline (sin límite de caracteres fijo, mínimo 1)
- **Provincia** — select con las 23 provincias + CABA de Argentina (lista estática en el componente)
- **Skills requeridas** — autocomplete:
  - Búsqueda debounced (~300ms) contra `GET /skills?q=...`
  - El usuario puede seleccionar una skill existente o confirmar una nueva (se crea via `POST /skills` antes de agregar)
  - Cada skill seleccionada es un chip removible con un toggle de nivel: BEGINNER / INTERMEDIATE / ADVANCED / PRO (default: INTERMEDIATE)
- **Botón "Publicar"** — llama a `POST /job-descriptions` con `user_id` hardcodeado del company_admin de MVP
- Al éxito: redirige a `/jobs` con toast de confirmación

#### `/jobs` — Listado de puestos

- Select de provincia arriba (opción "Todas las provincias" por defecto). Filtra llamando a `GET /job-descriptions?province=...`
- Cards por JD:
  - Título (bold)
  - Provincia
  - Publicado por: nombre del company_admin
  - Skills como chips coloreados por nivel (gris=BEGINNER, azul=INTERMEDIATE, naranja=ADVANCED, violeta=PRO)
  - Fecha de publicación
- Estado vacío: "No hay puestos publicados" cuando la lista es vacía
- Botón "Publicar puesto" visible en la página para navegar a `/new-job`

### AppLayout

Se agrega `"empresa"` como tercer valor de `userRole` en `AppLayoutProps`. Los links de navegación para empresa: "Puestos" (`/jobs`) e "Nuevo Puesto" (`/new-job`). Usuario hardcodeado: `"Empresa Global S.A."`.

### `api.ts`

Se agregan los tipos e helpers:

```typescript
// Skills
export interface Skill { id: number; name: string }
export const skills = {
  search: (q: string) => request<Skill[]>(`/skills?q=${encodeURIComponent(q)}`),
  create: (name: string) => request<Skill>("/skills", { method: "POST", body: JSON.stringify({ name }) }),
}

// Job Descriptions
export interface SkillRequirement { skill_id: number; skill_name: string; level: SkillLevel }
export type SkillLevel = "BEGINNER" | "INTERMEDIATE" | "ADVANCED" | "PRO"
export interface PostedBy { id: number; first_name: string; last_name: string; email: string }
export interface JobDescription { id: number; title: string; description: string; province: string; posted_by: PostedBy; required_skills: SkillRequirement[]; created_at: string }
export interface JobDescriptionCreate { user_id: number; title: string; description: string; province: string; required_skills: { skill_id: number; level: SkillLevel }[] }
export const jobDescriptions = {
  list: (province?: string) => request<JobDescription[]>(`/job-descriptions${province ? `?province=${encodeURIComponent(province)}` : ""}`),
  create: (data: JobDescriptionCreate) => request<JobDescription>("/job-descriptions", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/job-descriptions/${id}`, { method: "DELETE" }),
}
```

---

## Flujo de datos

### Crear una JD

1. Usuario escribe skill → frontend debounce 300ms → `GET /skills?q=texto`
2. Selecciona skill existente → agrega `{skill_id, level: "INTERMEDIATE"}` a lista local
3. Escribe skill nueva y confirma → `POST /skills {name}` → obtiene `skill_id` → agrega a lista local
4. Click "Publicar" → `POST /job-descriptions {user_id, title, province, required_skills}`
5. 201 → redirige a `/jobs`

### Listar JDs

1. Carga `/jobs` → `GET /job-descriptions` (sin filtro)
2. Usuario selecciona provincia → `GET /job-descriptions?province=Córdoba`

---

## Manejo de errores

| Situación | API | UI |
|---|---|---|
| Título vacío | 422 Pydantic | Error inline en campo |
| `required_skills` vacío | 422 Pydantic | Error inline en skills |
| `user_id` no existe | 404 | Toast de error |
| `user_id` no es company_admin | 403 | Toast de error |
| DELETE de JD inexistente | 404 | Toast de error |
| Sin resultados en `/jobs` | 200 `[]` | Estado vacío |

---

## Decisiones y trade-offs

- **Modelo de datos B (association table):** elegido sobre JSON column. Permite futura búsqueda de JDs por skill con join simple. El costo es mínimo (un insert adicional por skill al crear la JD).
- **user_id hardcodeado en frontend:** sin auth en MVP, igual que el dashboard hardcodea "Lucía Ramírez". Cuando se sume auth, el `user_id` viene del token.
- **Sin paginación:** la lista de JDs es plana para el MVP. Se agrega offset/limit cuando el volumen lo justifique.
- **Provincias como VARCHAR:** en lugar de enum de BD, para evitar migraciones si cambia la lista. La validación es responsabilidad del frontend (select estático).
- **Skills case-insensitive:** el seed normaliza en title-case. El `POST /skills` hace upsert por nombre (ILIKE) para evitar duplicados "python" / "Python".
