# Student Skills Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let students manage a personal skill list (add with level, remove) via a new `/student/skills` page backed by a new `user_skills` backend module.

**Architecture:** New `app/modules/user_skills/` backend module following the repository → service → router pattern; routes registered under the existing `/students` prefix. Frontend page mirrors `NuevoPuesto.tsx`'s skill autocomplete UX but saves each change to the API immediately (no single submit). No tests per project preference.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.x (backend), React / TypeScript / TanStack Query / Wouter / Tailwind / shadcn (frontend)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `app/modules/user_skills/__init__.py` | Package marker |
| Create | `app/modules/user_skills/models.py` | `UserSkill` SQLAlchemy model |
| Create | `app/modules/user_skills/schemas.py` | `UserSkillCreate`, `UserSkillResponse` Pydantic schemas |
| Create | `app/modules/user_skills/repository.py` | DB queries: list (with JOIN for skill name), add, remove |
| Create | `app/modules/user_skills/service.py` | Business logic, user lookup, error raising |
| Create | `app/modules/user_skills/router.py` | GET/POST/DELETE endpoints under `/students/{email}/skills` |
| Modify | `app/main.py` | Import and register new router |
| Modify | `frontend/src/lib/api.ts` | Add `UserSkill`, `UserSkillCreate` types + `userSkills` client |
| Create | `frontend/src/pages/MisHabilidades.tsx` | Student skills management page |
| Modify | `frontend/src/App.tsx` | Register `/student/skills` route |

---

### Task 1: Backend — `user_skills` module

**Files:**
- Create: `app/modules/user_skills/__init__.py`
- Create: `app/modules/user_skills/models.py`
- Create: `app/modules/user_skills/schemas.py`
- Create: `app/modules/user_skills/repository.py`
- Create: `app/modules/user_skills/service.py`
- Create: `app/modules/user_skills/router.py`
- Modify: `app/main.py`

- [ ] **Step 1: Create the package marker**

```bash
touch /home/dev/capacitaya/app/modules/user_skills/__init__.py
```

- [ ] **Step 2: Create `app/modules/user_skills/models.py`**

`SkillLevel` is imported from the job descriptions module (that's where it lives). The `UniqueConstraint` prevents a student from adding the same skill twice.

```python
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.modules.job_descriptions.models import SkillLevel


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id"), nullable=False
    )
    level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, name="skill_level"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Create `app/modules/user_skills/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.job_descriptions.models import SkillLevel


class UserSkillCreate(BaseModel):
    skill_id: int
    level: SkillLevel


class UserSkillResponse(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    level: SkillLevel
    created_at: datetime

    model_config = ConfigDict(from_attributes=False)
```

`from_attributes=False` because responses are built manually (not mapped directly from the ORM object — we need `skill_name` from a JOIN).

- [ ] **Step 4: Create `app/modules/user_skills/repository.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.job_descriptions.models import SkillLevel
from app.modules.skills.models import Skill
from app.modules.user_skills.models import UserSkill


def find_by_user(db: Session, user_id: int) -> list[tuple[UserSkill, str]]:
    stmt = (
        select(UserSkill, Skill.name)
        .join(Skill, UserSkill.skill_id == Skill.id)
        .where(UserSkill.user_id == user_id)
        .order_by(UserSkill.created_at)
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def find_one(db: Session, user_id: int, skill_id: int) -> UserSkill | None:
    stmt = select(UserSkill).where(
        UserSkill.user_id == user_id,
        UserSkill.skill_id == skill_id,
    )
    return db.scalar(stmt)


def add(db: Session, user_id: int, skill_id: int, level: SkillLevel) -> UserSkill:
    user_skill = UserSkill(user_id=user_id, skill_id=skill_id, level=level)
    db.add(user_skill)
    db.commit()
    db.refresh(user_skill)
    return user_skill


def remove(db: Session, user_id: int, skill_id: int) -> bool:
    user_skill = find_one(db, user_id, skill_id)
    if user_skill is None:
        return False
    db.delete(user_skill)
    db.commit()
    return True
```

- [ ] **Step 5: Create `app/modules/user_skills/service.py`**

```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.skills.models import Skill
from app.modules.user_skills import repository
from app.modules.user_skills.schemas import UserSkillCreate, UserSkillResponse
from app.modules.users import repository as users_repository


def _get_user_or_404(db: Session, email: str):
    user = users_repository.find_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def list_for_user(db: Session, email: str) -> list[UserSkillResponse]:
    user = _get_user_or_404(db, email)
    rows = repository.find_by_user(db, user.id)
    return [
        UserSkillResponse(
            id=us.id,
            skill_id=us.skill_id,
            skill_name=skill_name,
            level=us.level,
            created_at=us.created_at,
        )
        for us, skill_name in rows
    ]


def add_skill(db: Session, email: str, data: UserSkillCreate) -> UserSkillResponse:
    user = _get_user_or_404(db, email)

    if repository.find_one(db, user.id, data.skill_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Skill already added")

    skill = db.get(Skill, data.skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    user_skill = repository.add(db, user.id, data.skill_id, data.level)
    return UserSkillResponse(
        id=user_skill.id,
        skill_id=user_skill.skill_id,
        skill_name=skill.name,
        level=user_skill.level,
        created_at=user_skill.created_at,
    )


def remove_skill(db: Session, email: str, skill_id: int) -> None:
    user = _get_user_or_404(db, email)
    removed = repository.remove(db, user.id, skill_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not in user's list")
```

- [ ] **Step 6: Create `app/modules/user_skills/router.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.user_skills import service
from app.modules.user_skills.schemas import UserSkillCreate, UserSkillResponse

router = APIRouter(prefix="/students", tags=["user-skills"])


@router.get("/{email}/skills", response_model=list[UserSkillResponse])
def list_skills(email: str, db: Session = Depends(get_db)) -> list[UserSkillResponse]:
    return service.list_for_user(db, email)


@router.post(
    "/{email}/skills",
    response_model=UserSkillResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_skill(
    email: str, payload: UserSkillCreate, db: Session = Depends(get_db)
) -> UserSkillResponse:
    return service.add_skill(db, email, payload)


@router.delete("/{email}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill(email: str, skill_id: int, db: Session = Depends(get_db)) -> None:
    service.remove_skill(db, email, skill_id)
```

- [ ] **Step 7: Register the router in `app/main.py`**

Add this import after the existing imports (around line 16, after `from app.modules.users.router import router as users_router`):

```python
from app.modules.user_skills.router import router as user_skills_router
```

Add this line in the body of the `app` module (after `app.include_router(student_gap_analyses_router, prefix="/api")`):

```python
app.include_router(user_skills_router, prefix="/api")
```

- [ ] **Step 8: Verify the app imports cleanly**

```bash
cd /home/dev/capacitaya && source .venv/bin/activate && python -c "from app.main import app; print('OK')"
```

Expected: prints `OK` with no errors.

---

### Task 2: Frontend API client — `userSkills`

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Append the following block at the end of `frontend/src/lib/api.ts`**

`SkillLevel` is already defined in the same file as `"BEGINNER" | "INTERMEDIATE" | "ADVANCED" | "PRO"`. Do not redefine it.

```typescript
// ─── User Skills ──────────────────────────────────────────────────────────────

export interface UserSkill {
  id: number;
  skill_id: number;
  skill_name: string;
  level: SkillLevel;
  created_at: string;
}

export interface UserSkillCreate {
  skill_id: number;
  level: SkillLevel;
}

export const userSkills = {
  list: (email: string) =>
    request<UserSkill[]>(`/students/${encodeURIComponent(email)}/skills`),
  add: (email: string, data: UserSkillCreate) =>
    request<UserSkill>(`/students/${encodeURIComponent(email)}/skills`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  remove: (email: string, skillId: number) =>
    request<void>(`/students/${encodeURIComponent(email)}/skills/${skillId}`, {
      method: "DELETE",
    }),
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

---

### Task 3: Create `MisHabilidades.tsx`

**Files:**
- Create: `frontend/src/pages/MisHabilidades.tsx`

This page mirrors NuevoPuesto's skill UX. Key differences:
- No title/description/province fields — skills only
- Loads existing skills from API on mount
- Each add/remove operation hits the API immediately (no single submit)
- Level changes use delete + re-add (no PATCH endpoint)

- [ ] **Step 1: Create the file**

```tsx
import React, { useCallback, useEffect, useState } from "react";
import { AppLayout } from "@/components/AppLayout";
import { Input } from "@/components/ui/input";
import { X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import {
  Skill,
  SkillLevel,
  UserSkill,
  skills as skillsApi,
  userSkills,
} from "@/lib/api";
import { LEVEL_COLORS, LEVEL_LABELS, SKILL_LEVELS } from "@/lib/constants";

// Hardcoded para MVP — reemplazar por email del token cuando se sume auth.
// Asegurate de que exista un usuario con este email y rol student en la BD.
const STUDENT_EMAIL = "estudiante@demo.com";

export function MisHabilidades() {
  const { toast } = useToast();
  const [mySkills, setMySkills] = useState<UserSkill[]>([]);
  const [skillQuery, setSkillQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Skill[]>([]);

  const { data: initialSkills } = useQuery({
    queryKey: ["user-skills", STUDENT_EMAIL],
    queryFn: () => userSkills.list(STUDENT_EMAIL),
  });

  useEffect(() => {
    if (initialSkills) setMySkills(initialSkills);
  }, [initialSkills]);

  const fetchSuggestions = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions([]);
      return;
    }
    setSuggestions(await skillsApi.search(q));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchSuggestions(skillQuery), 300);
    return () => clearTimeout(timer);
  }, [skillQuery, fetchSuggestions]);

  const addSkill = async (skill: Skill | null, name?: string) => {
    let s = skill;
    if (!s && name) {
      try {
        s = await skillsApi.create(name);
      } catch {
        toast({ title: "Error al crear skill", variant: "destructive" });
        return;
      }
    }
    if (!s) return;
    if (mySkills.some((sk) => sk.skill_id === s!.id)) return;
    try {
      const added = await userSkills.add(STUDENT_EMAIL, {
        skill_id: s.id,
        level: "INTERMEDIATE",
      });
      setMySkills((prev) => [...prev, added]);
    } catch {
      toast({ title: "Error al guardar skill", variant: "destructive" });
    }
    setSkillQuery("");
    setSuggestions([]);
  };

  const removeSkill = async (skillId: number) => {
    try {
      await userSkills.remove(STUDENT_EMAIL, skillId);
      setMySkills((prev) => prev.filter((s) => s.skill_id !== skillId));
    } catch {
      toast({ title: "Error al eliminar skill", variant: "destructive" });
    }
  };

  const updateLevel = async (skill: UserSkill, level: SkillLevel) => {
    try {
      await userSkills.remove(STUDENT_EMAIL, skill.skill_id);
      const updated = await userSkills.add(STUDENT_EMAIL, {
        skill_id: skill.skill_id,
        level,
      });
      setMySkills((prev) =>
        prev.map((s) => (s.skill_id === skill.skill_id ? updated : s))
      );
    } catch {
      toast({ title: "Error al actualizar nivel", variant: "destructive" });
    }
  };

  const queryLower = skillQuery.toLowerCase();
  const canAddNew =
    skillQuery.trim().length > 0 &&
    !suggestions.some((s) => s.name.toLowerCase() === queryLower);

  return (
    <AppLayout activePage="Mis Habilidades" userRole="student" userName="Estudiante">
      <div className="max-w-2xl">
        <h2 className="text-xl font-bold mb-6">Mis habilidades</h2>

        <div className="space-y-5 bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
          <div>
            <label className="block text-sm font-medium mb-1">
              Buscá o agregá una habilidad
            </label>
            <div className="relative">
              <Input
                value={skillQuery}
                onChange={(e) => setSkillQuery(e.target.value)}
                placeholder="Ej: Excel, atención al cliente..."
                onKeyDown={(e) => {
                  if (e.key === "Enter" && skillQuery.trim()) {
                    e.preventDefault();
                    addSkill(null, skillQuery.trim());
                  }
                }}
              />
              {(suggestions.length > 0 || canAddNew) && (
                <div className="absolute z-10 w-full bg-white border border-slate-200 rounded-xl shadow-lg mt-1">
                  {suggestions.map((s) => (
                    <button
                      key={s.id}
                      className="w-full text-left px-4 py-2 text-sm hover:bg-slate-50 first:rounded-t-xl"
                      onClick={() => addSkill(s)}
                    >
                      {s.name}
                    </button>
                  ))}
                  {canAddNew && (
                    <button
                      className="w-full text-left px-4 py-2 text-sm text-[#4F46E5] hover:bg-indigo-50 last:rounded-b-xl border-t border-slate-100"
                      onClick={() => addSkill(null, skillQuery.trim())}
                    >
                      + Agregar &quot;{skillQuery}&quot;
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {mySkills.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-4">
              Todavía no agregaste ninguna habilidad.
            </p>
          )}

          {mySkills.length > 0 && (
            <div className="space-y-2">
              {mySkills.map((sk) => (
                <div key={sk.skill_id} className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm w-36 shrink-0">
                    {sk.skill_name}
                  </span>
                  <div className="flex gap-1 flex-wrap">
                    {SKILL_LEVELS.map((l) => (
                      <button
                        key={l}
                        onClick={() => updateLevel(sk, l)}
                        className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
                          sk.level === l
                            ? `${LEVEL_COLORS[l]} border-transparent`
                            : "bg-white border-slate-200 text-slate-500"
                        }`}
                      >
                        {LEVEL_LABELS[l]}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => removeSkill(sk.skill_id)}
                    className="text-slate-400 hover:text-red-400 ml-auto"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
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
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

---

### Task 4: Register route in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the import**

After the existing student page imports, add:

```typescript
import { MisHabilidades } from "@/pages/MisHabilidades";
```

- [ ] **Step 2: Add the route**

After `<Route path="/student/canal-tutor" component={CanalTutor} />`, add:

```tsx
<Route path="/student/skills" component={MisHabilidades} />
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.
