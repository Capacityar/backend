# capacityAr — Plataforma IA de Brecha de Habilidades

> Proyecto universitario de Ingeniería de Software I (nota 10).
> Rol: **Scrum Master** en equipo de 13 personas.

Plataforma de análisis de brecha de habilidades y capacitación IT con IA para PYMES argentinas. MVP desplegado en Render con integración de Groq Llama + Gemini.

Stack:

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React 19, Vite, Tailwind CSS
- **Deploy**: Render (backend + frontend como estático) + Neon (PostgreSQL serverless)

**Aprendizajes clave:**
- Coordinación de ceremonias ágiles en equipo multidisciplinario
- Arquitectura backend modular (router/service/repository)
- Integración de IA generativa con fallback mock
- Deploy serverless con CI/CD

---

## Estructura del proyecto

```text
app/                          # Backend FastAPI
  main.py
  config.py
  database.py
  modules/
    users/
    learning_paths/
    attempts/
    resources/
    job_descriptions/

frontend/
  artifacts/
    capacitaya/               # App React/Vite (standalone)
      src/
      public/
      package.json
      vite.config.ts
      Dockerfile
```

### Organización del backend (por módulo)

Cada módulo sigue capas con responsabilidad única:

- `router.py` — endpoints HTTP y dependencias FastAPI
- `service.py` — reglas de negocio y manejo de errores
- `repository.py` — acceso a datos con SQLAlchemy
- `models.py` — modelos y tablas
- `schemas.py` — contratos Pydantic de entrada/salida

---

## Desarrollo local con Docker

Es la forma recomendada. Levanta el backend, el frontend, la base de datos y pgAdmin con un solo comando.

```bash
cp .env.example .env
docker compose up
```

| Servicio | URL |
|---|---|
| Backend (API) | http://localhost:8000 |
| Frontend | http://localhost:3000 |
| Documentación de endpoints (Swagger) | http://localhost:8000/docs |
| pgAdmin | http://localhost:8888 |

El frontend usa hot-reload: los cambios en `frontend/artifacts/capacitaya/src/` se reflejan en el browser sin reiniciar el contenedor.

Para reconstruir las imágenes (por ejemplo, al agregar dependencias npm o pip):

```bash
docker compose up --build
```

---

## Desarrollo local sin Docker

### Backend

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Para usar SQLite en lugar de PostgreSQL, poner en `.env`:

```env
DATABASE_URL=sqlite:///./capacity_ar_local.db
```

### Frontend

```bash
cd frontend/artifacts/capacitaya
npm install
PORT=3000 BASE_PATH=/ npm run dev
```

---

## Integración frontend ↔ API

El cliente tipado vive en `frontend/src/lib/api.ts` y expone cuatro namespaces que mapean directamente a los endpoints del backend.

### Namespaces disponibles

```ts
import { users, learningPaths, attempts } from "@/lib/api";
```

| Namespace | Funciones |
|---|---|
| `users` | `list()`, `get(id)`, `create(data)` |
| `learningPaths` | `list()`, `get(id)`, `getByStudent(email)` |
| `attempts` | `create(data)`, `get(id)`, `getByStudent(email)` |

### Cómo usar con React Query

Todas las funciones devuelven una `Promise` y están pensadas para usarse con `useQuery` (lecturas) o `useMutation` (escrituras):

```tsx
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { learningPaths, attempts } from "@/lib/api";

// Lectura: learning path de un estudiante
const { data, isLoading, error } = useQuery({
  queryKey: ["learning-paths", email],
  queryFn: () => learningPaths.getByStudent(email),
});

// Escritura: registrar un intento de ejercicio
const queryClient = useQueryClient();
const mutation = useMutation({
  mutationFn: attempts.create,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["attempts", email] });
  },
});

mutation.mutate({
  student_email: "lucia@ejemplo.com",
  learning_path_id: 1,
  module_index: 0,
  unit_index: 0,
  exercise_index: 0,
  answer: "La respuesta del alumno",
});
```

### Proxy en desarrollo

En dev (`docker compose up`), el frontend corre en `:3000` y el backend en `:8000`. Vite intercepta automáticamente cualquier request a `/api/*` y la forwarda al backend — no se necesita configurar CORS ni URLs absolutas. En producción (Render), FastAPI sirve el frontend como estático, por lo que `/api/*` llega directamente al mismo servidor.

### Tipos exportados

El archivo `api.ts` exporta todos los tipos necesarios:

```ts
import type { User, LearningPath, Module, Unit, Exercise, Attempt } from "@/lib/api";
```

---

## Deploy en Render

El deploy es automático desde la branch `main` vía webhook de GitHub.

### Qué hace Render al deployar

1. Instala Node.js (vía Nix)
2. Instala dependencias npm y hace el build del frontend (`npm run build`)
3. Instala dependencias Python
4. Inicia el servidor con uvicorn

El frontend queda compilado como archivos estáticos en `frontend/artifacts/capacitaya/dist/public/` y FastAPI los sirve directamente. Las rutas de API viven bajo `/api/*`.

### Variables de entorno en Render

Configurar en **Environment** del Web Service (no en `render.yaml`):

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | URL externa del PostgreSQL (Neon u otro). La app normaliza `postgres://` a `postgresql+psycopg://` automáticamente. |
| `APP_ENV` | `production` |
| `APP_DEBUG` | `false` |
| `PLAN_GENERATOR` | `groq` o `gemini` (default: `mock` si no se setea) |
| `GROQ_API_KEY` | API key de Groq |
| `GEMINI_API_KEY` | API key de Google Gemini |
| `PORT` | 3000 (de FastAPI) |
### Base de datos

Las tablas se crean automáticamente al iniciar la app con `Base.metadata.create_all`. Cuando el modelo empiece a cambiar con datos reales en producción, el siguiente paso es sumar Alembic para migraciones.

---

## Buenas prácticas para este MVP

- Módulos por capacidad de negocio, no por tipo técnico global.
- Reglas de negocio en `service.py`, nunca en routers.
- SQLAlchemy aislado en `repository.py`.
- Auth diferida intencionalmente hasta cerrar el flujo mínimo.
- `create_all` sólo en MVP; migraciones con Alembic cuando haya cambios de schema en producción.
