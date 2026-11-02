# Tutor Pages API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `/tutor`, `/tutor/companies`, and `/tutor/jobs` to fetch real user data from `GET /api/users` filtered by role, replacing all hardcoded data.

**Architecture:** Add an optional `?role=` query param to the backend `GET /users` endpoint (repository → service → router), update the frontend API client to pass it, replace hardcoded rows in `PanelTutor.tsx` with live data, add a new `TutorCompanias.tsx` page, and register both new routes in `App.tsx`.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.x (backend), React / TypeScript / TanStack Query / Wouter (frontend), pytest + httpx (tests)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `app/modules/users/repository.py` | Add optional `role` filter to `find_all` |
| Modify | `app/modules/users/service.py` | Pass `role` through to repository |
| Modify | `app/modules/users/router.py` | Expose `?role=` as a Query param |
| Create | `tests/__init__.py` | Makes `tests/` a package |
| Create | `tests/conftest.py` | In-memory SQLite TestClient fixture |
| Create | `tests/modules/__init__.py` | |
| Create | `tests/modules/users/__init__.py` | |
| Create | `tests/modules/users/test_router.py` | Tests for role filtering |
| Modify | `frontend/src/lib/api.ts` | Add `role` to `users.list()` params |
| Modify | `frontend/src/pages/PanelTutor.tsx` | Fetch students from API, replace hardcoded rows |
| Create | `frontend/src/pages/TutorCompanias.tsx` | Company admins list page |
| Modify | `frontend/src/App.tsx` | Add `/tutor/companies` and `/tutor/jobs` routes |

---

### Task 1: Set up test infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/modules/__init__.py`
- Create: `tests/modules/users/__init__.py`

- [ ] **Step 1: Install dev dependencies**

Run from the repo root (with the venv active):

```bash
pip install -e ".[dev]"
```

Expected output ends with: `Successfully installed ...`

- [ ] **Step 2: Create the test package files**

Create four empty `__init__.py` files:

```bash
mkdir -p tests/modules/users
touch tests/__init__.py tests/modules/__init__.py tests/modules/users/__init__.py
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

_ENGINE = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}
)
_Session = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)

# Create all tables once when the module is loaded.
# By this point app.main has already been imported (and with it all models),
# so Base.metadata contains every table.
Base.metadata.create_all(bind=_ENGINE)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Drop and recreate all tables before each test for full isolation."""
    Base.metadata.drop_all(bind=_ENGINE)
    Base.metadata.create_all(bind=_ENGINE)


@pytest.fixture
def db(_clean_tables):
    session = _Session()
    yield session
    session.close()


@pytest.fixture
def client(db):
    """
    TestClient without context manager — does NOT trigger the app lifespan,
    which would call create_db_tables() against the real DB URL.
    The db dependency is overridden to use the in-memory SQLite session.
    """
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
```

- [ ] **Step 4: Verify pytest discovers the suite (no tests yet = 0 collected is fine)**

```bash
pytest --collect-only
```

Expected: `no tests ran` or `0 items` — no errors.

---

### Task 2: Backend — add `?role=` filter

**Files:**
- Modify: `app/modules/users/repository.py`
- Modify: `app/modules/users/service.py`
- Modify: `app/modules/users/router.py`
- Test: `tests/modules/users/test_router.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/modules/users/test_router.py`:

```python
def test_list_users_filter_by_role_student(client):
    client.post("/api/users", json={"first_name": "Ana", "last_name": "López", "email": "ana@test.com", "role": "student"})
    client.post("/api/users", json={"first_name": "Carlos", "last_name": "Pérez", "email": "carlos@test.com", "role": "student"})
    client.post("/api/users", json={"first_name": "Empresa", "last_name": "SA", "email": "empresa@test.com", "role": "company_admin"})

    response = client.get("/api/users?role=student")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(u["role"] == "student" for u in data)


def test_list_users_filter_by_role_company_admin(client):
    client.post("/api/users", json={"first_name": "Ana", "last_name": "López", "email": "ana@test.com", "role": "student"})
    client.post("/api/users", json={"first_name": "Empresa", "last_name": "SA", "email": "empresa@test.com", "role": "company_admin"})

    response = client.get("/api/users?role=company_admin")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["role"] == "company_admin"


def test_list_users_no_filter_returns_all(client):
    client.post("/api/users", json={"first_name": "Ana", "last_name": "López", "email": "ana@test.com", "role": "student"})
    client.post("/api/users", json={"first_name": "Empresa", "last_name": "SA", "email": "empresa@test.com", "role": "company_admin"})

    response = client.get("/api/users")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_users_invalid_role_returns_422(client):
    response = client.get("/api/users?role=unicorn")
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/modules/users/test_router.py -v
```

Expected: 4 FAILs (role param not accepted yet).

- [ ] **Step 3: Update `app/modules/users/repository.py`**

Replace the entire `find_all` function (apply the role filter before pagination so offset/limit count only matching rows):

```python
from app.modules.users.models import User, UserRole


def find_all(
    db: Session,
    offset: int = 0,
    limit: int = 100,
    role: UserRole | None = None,
) -> list[User]:
    statement = select(User).order_by(User.id)
    if role is not None:
        statement = statement.where(User.role == role)
    statement = statement.offset(offset).limit(limit)
    return list(db.scalars(statement).all())
```

The full updated file:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserCreate, UserUpdate


def find_all(
    db: Session,
    offset: int = 0,
    limit: int = 100,
    role: UserRole | None = None,
) -> list[User]:
    statement = select(User).order_by(User.id)
    if role is not None:
        statement = statement.where(User.role == role)
    statement = statement.offset(offset).limit(limit)
    return list(db.scalars(statement).all())


def find_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def find_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def create(db: Session, data: UserCreate) -> User:
    user = User(**data.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update(db: Session, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def delete(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
```

- [ ] **Step 4: Update `app/modules/users/service.py`**

Full updated file:

```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.users import repository
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserCreate, UserUpdate


def list_users(
    db: Session,
    offset: int = 0,
    limit: int = 100,
    role: UserRole | None = None,
) -> list[User]:
    return repository.find_all(db, offset=offset, limit=limit, role=role)


def get_user(db: Session, user_id: int) -> User:
    user = repository.find_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def create_user(db: Session, data: UserCreate) -> User:
    if repository.find_by_email(db, data.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    return repository.create(db, data)


def update_user(db: Session, user_id: int, data: UserUpdate) -> User:
    user = get_user(db, user_id)
    if data.email is not None:
        existing_user = repository.find_by_email(db, data.email)
        if existing_user is not None and existing_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    return repository.update(db, user, data)


def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)
    repository.delete(db, user)
```

- [ ] **Step 5: Update `app/modules/users/router.py`**

Full updated file:

```python
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.users import service
from app.modules.users.models import UserRole
from app.modules.users.schemas import UserCreate, UserResponse, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    role: UserRole | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    return service.list_users(db, offset=offset, limit=limit, role=role)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    return service.create_user(db, payload)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    return service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> UserResponse:
    return service.update_user(db, user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    service.delete_user(db, user_id)
```

- [ ] **Step 6: Run tests — all should pass**

```bash
pytest tests/modules/users/test_router.py -v
```

Expected: 4 PASSes.

- [ ] **Step 7: Commit**

```bash
git add app/modules/users/repository.py app/modules/users/service.py app/modules/users/router.py tests/
git commit -m "feat: add role filter to GET /users endpoint"
```

---

### Task 3: Frontend API client — add `role` param to `users.list()`

**Files:**
- Modify: `frontend/src/lib/api.ts` (lines 125–133)

- [ ] **Step 1: Update `users.list()` in `frontend/src/lib/api.ts`**

Replace the `users` object:

```typescript
export const users = {
  list: (params?: { offset?: number; limit?: number; role?: UserRole }) => {
    const entries = Object.entries(params ?? {}).filter(([, v]) => v !== undefined);
    const qs = new URLSearchParams(entries as [string, string][]).toString();
    return request<User[]>(`/users${qs ? `?${qs}` : ""}`);
  },
  get: (id: number) => request<User>(`/users/${id}`),
  create: (data: UserCreate) =>
    request<User>("/users", { method: "POST", body: JSON.stringify(data) }),
};
```

The `filter(([, v]) => v !== undefined)` prevents `undefined` values from being serialised as the literal string `"undefined"` in the query string.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: support role filter in users.list() API client"
```

---

### Task 4: Update `PanelTutor.tsx` to use the API

**Files:**
- Modify: `frontend/src/pages/PanelTutor.tsx`

- [ ] **Step 1: Replace the entire file**

```tsx
import React from "react";
import { AppLayout } from "@/components/AppLayout";
import { AlertTriangle, Search, ChevronRight } from "lucide-react";
import { Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { users, User } from "@/lib/api";

function formatRelativeDate(dateStr: string): string {
  const diffDays = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000);
  if (diffDays === 0) return "Hoy";
  if (diffDays === 1) return "Hace 1 día";
  if (diffDays < 30) return `Hace ${diffDays} días`;
  return new Date(dateStr).toLocaleDateString("es-AR");
}

export function PanelTutor() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["users", "student"],
    queryFn: () => users.list({ role: "student" }),
  });

  return (
    <AppLayout activePage="Mis Candidatos" userRole="tutor" userName="Ana García">
      <div className="space-y-6 pb-12">
        {/* Banner Alerta */}
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center justify-between text-red-800 cursor-pointer hover:bg-red-100 transition-colors">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <span className="font-bold">⚠ 2 candidatos llevan más de 3 días inactivos</span>
          </div>
          <div className="font-semibold flex items-center gap-1 text-sm">
            Revisar ahora <ChevronRight className="w-4 h-4" />
          </div>
        </div>

        {/* Filtros */}
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full sm:w-80">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar candidato..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>
          <div className="flex overflow-x-auto w-full sm:w-auto gap-2 pb-2 sm:pb-0">
            <button className="px-4 py-2 bg-[#4F46E5] text-white text-sm font-semibold rounded-lg whitespace-nowrap">Todos</button>
            <button className="px-4 py-2 bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 text-sm font-medium rounded-lg whitespace-nowrap transition-colors">En progreso</button>
            <button className="px-4 py-2 bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 text-sm font-medium rounded-lg whitespace-nowrap transition-colors">Requiere atención</button>
            <button className="px-4 py-2 bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 text-sm font-medium rounded-lg whitespace-nowrap transition-colors">Inactivos</button>
          </div>
        </div>

        {/* Tabla */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          {isLoading && (
            <div className="text-center text-slate-400 py-12">Cargando candidatos...</div>
          )}
          {isError && (
            <div className="text-center text-slate-500 py-12">No se pudieron cargar los candidatos.</div>
          )}
          {data && data.length === 0 && (
            <div className="text-center text-slate-400 py-12">No hay candidatos registrados.</div>
          )}
          {data && data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-xs uppercase tracking-wider text-[#64748B] font-bold">
                    <th className="p-4 pl-6">Candidato</th>
                    <th className="p-4">Email</th>
                    <th className="p-4">Progreso general</th>
                    <th className="p-4">Última actividad</th>
                    <th className="p-4">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {data.map((user: User) => (
                    <tr key={user.id} className="hover:bg-slate-50 transition-colors cursor-pointer group">
                      <td className="p-4 pl-6">
                        <Link href="/detalle-candidato">
                          <div className="font-bold text-[#1E293B] group-hover:text-[#4F46E5] transition-colors">
                            {user.first_name} {user.last_name}
                          </div>
                        </Link>
                      </td>
                      <td className="p-4 text-[#64748B]">{user.email}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-slate-300 rounded-full" style={{ width: "0%" }}></div>
                          </div>
                          <span className="font-semibold text-[#1E293B]">0%</span>
                        </div>
                      </td>
                      <td className="p-4 text-[#64748B]">{formatRelativeDate(user.created_at)}</td>
                      <td className="p-4">
                        <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-slate-100 text-slate-500 uppercase">
                          Sin iniciar
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PanelTutor.tsx
git commit -m "feat: fetch students from API in PanelTutor"
```

---

### Task 5: Create `TutorCompanias.tsx`

**Files:**
- Create: `frontend/src/pages/TutorCompanias.tsx`

- [ ] **Step 1: Create the file**

```tsx
import React from "react";
import { AppLayout } from "@/components/AppLayout";
import { useQuery } from "@tanstack/react-query";
import { users, User } from "@/lib/api";

export function TutorCompanias() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["users", "company_admin"],
    queryFn: () => users.list({ role: "company_admin" }),
  });

  return (
    <AppLayout activePage="Empresas" userRole="tutor" userName="Ana García">
      <div className="space-y-6 pb-12">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          {isLoading && (
            <div className="text-center text-slate-400 py-12">Cargando empresas...</div>
          )}
          {isError && (
            <div className="text-center text-slate-500 py-12">No se pudieron cargar las empresas.</div>
          )}
          {data && data.length === 0 && (
            <div className="text-center text-slate-400 py-12">No hay empresas registradas.</div>
          )}
          {data && data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-xs uppercase tracking-wider text-[#64748B] font-bold">
                    <th className="p-4 pl-6">Nombre</th>
                    <th className="p-4">Email</th>
                    <th className="p-4">Fecha de registro</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {data.map((user: User) => (
                    <tr key={user.id} className="hover:bg-slate-50 transition-colors">
                      <td className="p-4 pl-6 font-bold text-[#1E293B]">
                        {user.first_name} {user.last_name}
                      </td>
                      <td className="p-4 text-[#64748B]">{user.email}</td>
                      <td className="p-4 text-[#64748B]">
                        {new Date(user.created_at).toLocaleDateString("es-AR")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TutorCompanias.tsx
git commit -m "feat: add TutorCompanias page listing company admins"
```

---

### Task 6: Register new routes in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the import for `TutorCompanias`**

In `frontend/src/App.tsx`, add after the existing `PanelTutor` import:

```typescript
import { TutorCompanias } from "@/pages/TutorCompanias";
```

- [ ] **Step 2: Add the two new routes**

In the `Router` function, add after `<Route path="/tutor" component={PanelTutor} />`:

```tsx
<Route path="/tutor/companies" component={TutorCompanias} />
<Route path="/tutor/jobs" component={ListadoPuestos} />
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add /tutor/companies and /tutor/jobs routes"
```

---

### Task 7: Manual smoke test

- [ ] **Step 1: Start the backend**

```bash
uvicorn app.main:app --reload
```

- [ ] **Step 2: Verify the role filter works**

```bash
curl "http://localhost:8000/api/users?role=student" | python3 -m json.tool
```

Expected: a JSON array where every object has `"role": "student"`.

```bash
curl "http://localhost:8000/api/users?role=company_admin" | python3 -m json.tool
```

Expected: a JSON array where every object has `"role": "company_admin"`.

- [ ] **Step 3: Start the frontend dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 4: Visit each route and verify**

| URL | Expected |
|---|---|
| `http://localhost:5173/tutor` | Table of students fetched from API (real names, emails, 0% progress) |
| `http://localhost:5173/tutor/companies` | Table of company_admin users |
| `http://localhost:5173/tutor/jobs` | Same ListadoPuestos page as `/companies/jobs` |
