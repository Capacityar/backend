# Gap Analysis from DB Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the PDF-upload gap analysis with a deterministic computation from the student's saved skills and the job description's required skills, generating the learning path in the same request.

**Architecture:** The `POST /api/gap-analyses` endpoint changes from multipart/form-data to JSON `{student_email, job_description_id}`. The service builds the `GapReport` by fetching from `user_skills` and `job_description_skills` and computing the gap arithmetically (no LLM). It then immediately calls the existing plan generator to create the learning path and returns `GapAnalysisWithPlanResponse`. The frontend removes PDF upload inputs and instead shows the gap table plus a learning path confirmation.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.x (backend), React / TypeScript / TanStack Query (frontend). No new dependencies.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `app/modules/gap_analysis/schemas.py` | Add `GapAnalysisFromSkillsCreate` |
| Modify | `app/modules/gap_analysis/service.py` | Add gap helpers + `create_gap_analysis_from_skills()` |
| Modify | `app/modules/gap_analysis/router.py` | Replace multipart POST with JSON endpoint |
| Modify | `frontend/src/lib/api.ts` | Add `GapAnalysisCreate`, `GapAnalysisWithPlan`, update `gapAnalyses.create()` |
| Modify | `frontend/src/pages/TutorGapAnalysis.tsx` | Remove PDF inputs, wire to new endpoint, show learning path |

---

### Task 1: Add `GapAnalysisFromSkillsCreate` to schemas

**Files:**
- Modify: `app/modules/gap_analysis/schemas.py`

- [ ] **Step 1: Add the new input schema**

Append to `app/modules/gap_analysis/schemas.py` after the existing `GapAnalysisInputs` class:

```python
class GapAnalysisFromSkillsCreate(BaseModel):
    student_email: EmailStr
    job_description_id: int
```

- [ ] **Step 2: Verify import is clean**

```bash
cd /home/dev/capacitaya && source .venv/bin/activate && python -c "from app.modules.gap_analysis.schemas import GapAnalysisFromSkillsCreate; print('OK')"
```

Expected: `OK`

---

### Task 2: Add gap computation helpers and `create_gap_analysis_from_skills` to service

**Files:**
- Modify: `app/modules/gap_analysis/service.py`

This is the core task. The service fetches student skills and JD skills, computes the gap deterministically, builds the `GapReport`, saves a `GapAnalysis` row, then calls the plan generator to create the learning path — all in one function.

**Existing functions in the file to keep untouched:** `generate_learning_path_for_student`, `get_gap_analysis`, `list_by_student`, `_validate_inputs`, `_extract_or_fail`, `_groq_extract_gap_report`, `_enrich_with_email`, `_build_extraction_prompt`, `_to_response`.

- [ ] **Step 1: Add new imports at the top of the file**

The file currently imports `from app.modules.learning_paths.schemas import GapReport`. Extend that import and add module-level repository imports:

Replace:
```python
from app.modules.learning_paths.schemas import GapReport
```

With:
```python
from app.modules.learning_paths.schemas import (
    CompanyInput,
    GapReport,
    GapSkill,
    RequiredSkill,
    SkillPriority,
    SkillStatus,
    StudentInput,
    StudentSkill,
    TargetRoleInput,
)
from app.modules.job_descriptions import repository as jd_repository
from app.modules.job_descriptions.models import JobDescription
from app.modules.user_skills import repository as us_repository
from app.modules.users import repository as users_repository
```

- [ ] **Step 2: Add module-level constants after the `logger` line**

Add after `logger = logging.getLogger(__name__)`:

```python
_LEVEL_INT: dict[str, int] = {
    "BEGINNER": 1,
    "INTERMEDIATE": 2,
    "ADVANCED": 3,
    "PRO": 4,
}

_PRIORITY_WEIGHT: dict[str, int] = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
```

- [ ] **Step 3: Add `create_gap_analysis_from_skills` and helpers**

Add these three functions **before** `generate_learning_path_for_student` (after `create_gap_analysis`):

```python
def create_gap_analysis_from_skills(
    db: Session,
    student_email: str,
    job_description_id: int,
    plan_generator: PlanGenerator,
    lp_repository: LearningPathRepository,
) -> GapAnalysisWithPlanResponse:
    student = users_repository.find_by_email(db, student_email)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado.")

    jd = jd_repository.find_by_id(db, job_description_id)
    if jd is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puesto no encontrado.")

    jd_skills = jd_repository.find_skills_for_jd(db, job_description_id)
    if not jd_skills:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El puesto no tiene habilidades requeridas.",
        )

    student_skill_rows = us_repository.find_by_user(db, student.id)

    company_user = users_repository.find_by_id(db, jd.user_id)
    company_name = (
        f"{company_user.first_name} {company_user.last_name}" if company_user else "Empresa"
    )
    company_email = company_user.email if company_user else ""

    gap_report = _build_gap_report(
        student=student,
        student_skill_rows=student_skill_rows,
        jd=jd,
        jd_skills=jd_skills,
        company_name=company_name,
    )

    stored = repository.save(
        db,
        GapAnalysis(
            student_email=student.email,
            company_email=company_email,
            readiness_score=gap_report.readiness_score,
            summary=gap_report.summary,
            gap_report_json=gap_report.model_dump_json(),
            student_doc_text="",
            position_doc_text="",
            learning_path_id=None,
            generator_used="skills",
        ),
    )

    learning_path = lp_service.create_learning_path(
        plan_generator, lp_repository, gap_report, db
    )

    stored.learning_path_id = learning_path.id
    db.commit()
    db.refresh(stored)

    return GapAnalysisWithPlanResponse(
        gap_analysis=_to_response(stored, gap_report),
        learning_path=learning_path,
    )


def _build_gap_report(
    student,
    student_skill_rows: list,
    jd: JobDescription,
    jd_skills: list,
    company_name: str,
) -> GapReport:
    # Build dict: skill_name.lower() → level int for fast lookup
    student_skills_dict: dict[str, int] = {
        name.lower(): _LEVEL_INT[us.level.value]
        for us, name in student_skill_rows
    }

    gap_skills: list[GapSkill] = []
    required_skills_for_role: list[RequiredSkill] = []

    for _skill_id, skill_name, jd_level in jd_skills:
        required_num = _LEVEL_INT[jd_level.value]
        current_num = student_skills_dict.get(skill_name.lower(), 0)
        gap = required_num - current_num

        if gap <= 0:
            skill_status = SkillStatus.READY
            skill_priority = SkillPriority.LOW
        elif gap == 1:
            skill_status = SkillStatus.NEEDS_WORK
            skill_priority = SkillPriority.MEDIUM
        else:
            skill_status = SkillStatus.MISSING
            skill_priority = SkillPriority.HIGH

        gap_skills.append(GapSkill(
            name=skill_name,
            current_level=min(current_num, 5),
            required_level=required_num,
            gap_level=gap,
            priority=skill_priority,
            status=skill_status,
        ))
        required_skills_for_role.append(RequiredSkill(
            name=skill_name,
            level=required_num,
            priority=skill_priority,
        ))

    # Weighted readiness score
    total_weight = sum(_PRIORITY_WEIGHT[gs.priority.value] for gs in gap_skills)
    if total_weight == 0:
        readiness_score = 100
    else:
        weighted_sum = sum(
            _PRIORITY_WEIGHT[gs.priority.value] * (
                min(gs.current_level, gs.required_level) / gs.required_level
                if gs.required_level > 0 else 1.0
            )
            for gs in gap_skills
        )
        readiness_score = round(weighted_sum / total_weight * 100)

    # Deterministic summary
    n_gaps = sum(1 for gs in gap_skills if gs.status != SkillStatus.READY)
    student_name = f"{student.first_name} {student.last_name}"
    if n_gaps == 0:
        summary = f"{student_name} cumple con el perfil requerido para {jd.title}."
    elif n_gaps == 1:
        summary = f"A {student_name} le falta 1 habilidad para alcanzar el perfil de {jd.title}."
    else:
        summary = f"A {student_name} le faltan {n_gaps} habilidades para alcanzar el perfil de {jd.title}."

    return GapReport(
        student=StudentInput(
            name=student_name,
            email=student.email,
            skills=[
                StudentSkill(name=name, level=_LEVEL_INT[us.level.value])
                for us, name in student_skill_rows
            ],
            interests=[],
        ),
        company=CompanyInput(name=company_name),
        target_role=TargetRoleInput(
            title=jd.title,
            required_skills=required_skills_for_role,
        ),
        summary=summary,
        readiness_score=readiness_score,
        skills=gap_skills,
    )
```

- [ ] **Step 4: Verify the app imports cleanly**

```bash
cd /home/dev/capacitaya && source .venv/bin/activate && python -c "from app.main import app; print('OK')"
```

Expected: `OK` (FutureWarning from Gemini library is pre-existing and OK)

---

### Task 3: Replace multipart endpoint with JSON endpoint in router

**Files:**
- Modify: `app/modules/gap_analysis/router.py`

Replace the entire file. The only change is the `create_gap_analysis` endpoint: multipart/form-data → JSON body, `GapAnalysisResponse` → `GapAnalysisWithPlanResponse`, calls new service function. All other endpoints stay identical.

- [ ] **Step 1: Replace the entire file**

```python
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.gap_analysis import service
from app.modules.gap_analysis.schemas import (
    GapAnalysisFromSkillsCreate,
    GapAnalysisResponse,
    GapAnalysisWithPlanResponse,
)
from app.modules.learning_paths.plan_generator.base import PlanGenerator
from app.modules.learning_paths.plan_generator.factory import get_plan_generator
from app.modules.learning_paths.repository.base import LearningPathRepository
from app.modules.learning_paths.repository.factory import get_learning_path_repository


router = APIRouter(prefix="/gap-analyses", tags=["gap-analyses"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=GapAnalysisWithPlanResponse,
)
def create_gap_analysis(
    payload: GapAnalysisFromSkillsCreate,
    db: Session = Depends(get_db),
    plan_generator: PlanGenerator = Depends(get_plan_generator),
    lp_repository: LearningPathRepository = Depends(get_learning_path_repository),
) -> GapAnalysisWithPlanResponse:
    return service.create_gap_analysis_from_skills(
        db=db,
        student_email=payload.student_email,
        job_description_id=payload.job_description_id,
        plan_generator=plan_generator,
        lp_repository=lp_repository,
    )


@router.get("/{gap_id}", response_model=GapAnalysisResponse)
def get_gap_analysis(
    gap_id: int, db: Session = Depends(get_db)
) -> GapAnalysisResponse:
    return service.get_gap_analysis(db, gap_id)


student_gap_analyses_router = APIRouter(prefix="/students", tags=["gap-analyses"])


@student_gap_analyses_router.get(
    "/{email}/gap-analyses", response_model=list[GapAnalysisResponse]
)
def list_by_student(
    email: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[GapAnalysisResponse]:
    return service.list_by_student(db, email, offset=offset, limit=limit)


@student_gap_analyses_router.post(
    "/{email}/generate-learning-path",
    status_code=status.HTTP_201_CREATED,
    response_model=GapAnalysisWithPlanResponse,
)
def generate_learning_path_for_student(
    email: str,
    db: Session = Depends(get_db),
    plan_generator: PlanGenerator = Depends(get_plan_generator),
    lp_repository: LearningPathRepository = Depends(get_learning_path_repository),
) -> GapAnalysisWithPlanResponse:
    return service.generate_learning_path_for_student(
        db=db,
        student_email=email,
        plan_generator=plan_generator,
        lp_repository=lp_repository,
    )
```

- [ ] **Step 2: Verify import**

```bash
cd /home/dev/capacitaya && source .venv/bin/activate && python -c "from app.main import app; print('OK')"
```

Expected: `OK`

---

### Task 4: Update `api.ts` — new types and `gapAnalyses.create()`

**Files:**
- Modify: `frontend/src/lib/api.ts`

Replace the entire `// ─── Gap Analyses` section at the bottom of the file. The key changes:
- Add `GapAnalysisCreate` input type (replaces the old `FormData` approach)
- Add `GapAnalysisWithPlan` response type (gap analysis + learning path combined)
- `gapAnalyses.create()` becomes a regular JSON request using the `request()` helper

- [ ] **Step 1: Find and replace the Gap Analyses section**

The current file ends with:
```typescript
// ─── Gap Analyses ─────────────────────────────────────────────────────────────

export interface GapSkill {
  ...
}
...
export const gapAnalyses = {
  create: async (formData: FormData): Promise<GapAnalysis> => {
    ...
  },
};
```

Replace everything from `// ─── Gap Analyses` to the end of the file with:

```typescript
// ─── Gap Analyses ─────────────────────────────────────────────────────────────

export interface GapSkill {
  name: string;
  current_level: number;
  required_level: number;
  gap_level: number;
  priority: SkillPriority;
  status: SkillStatus;
}

export interface GapReportData {
  id: number | null;
  summary: string;
  readiness_score: number;
  skills: GapSkill[];
}

export interface GapAnalysis {
  id: number;
  student_email: string;
  company_email: string;
  readiness_score: number;
  summary: string;
  gap_report: GapReportData;
  learning_path_id: number | null;
  generator_used: string;
  created_at: string;
}

export interface GapAnalysisCreate {
  student_email: string;
  job_description_id: number;
}

export interface GapAnalysisWithPlan {
  gap_analysis: GapAnalysis;
  learning_path: LearningPath;
}

export const gapAnalyses = {
  create: (data: GapAnalysisCreate) =>
    request<GapAnalysisWithPlan>("/gap-analyses", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: errors only in `TutorGapAnalysis.tsx` (which still uses old types) and the pre-existing `ListadoPuestosEvaluacion.tsx` error. No new errors elsewhere.

---

### Task 5: Rewrite `TutorGapAnalysis.tsx` — remove PDFs, show learning path

**Files:**
- Modify: `frontend/src/pages/TutorGapAnalysis.tsx`

Changes from the current version:
- Remove `studentDocRef`, `positionDocRef`, `studentDoc`, `positionDoc` state and refs
- Remove both PDF upload `<div>` zones and hidden `<input type="file">` elements
- `canSubmit` no longer requires files — just `selectedStudent && selectedJd && !isPending`
- `handleSubmit` sends JSON `{ student_email, job_description_id }` via `gapAnalyses.create()`
- `result` type changes from `GapAnalysis` to `GapAnalysisWithPlan`
- Result card shows `result.gap_analysis.readiness_score`, `result.gap_analysis.summary`, skills table, plus a "Plan de aprendizaje generado" confirmation line

- [ ] **Step 1: Replace the entire file**

```tsx
import React, { useState } from "react";
import { AppLayout } from "@/components/AppLayout";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useQuery } from "@tanstack/react-query";
import {
  GapAnalysisWithPlan,
  JobDescription,
  User,
  gapAnalyses,
  jobDescriptions,
  users,
} from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  READY: "bg-emerald-50 text-emerald-700",
  NEEDS_WORK: "bg-amber-50 text-amber-700",
  MISSING: "bg-red-50 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  READY: "Listo",
  NEEDS_WORK: "Necesita trabajo",
  MISSING: "Faltante",
};

export function TutorGapAnalysis() {
  const [studentId, setStudentId] = useState<string>("");
  const [jdId, setJdId] = useState<string>("");
  const [isPending, setIsPending] = useState(false);
  const [result, setResult] = useState<GapAnalysisWithPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: studentList } = useQuery({
    queryKey: ["users", "student"],
    queryFn: () => users.list({ role: "student" }),
  });

  const { data: jdList } = useQuery({
    queryKey: ["job-descriptions"],
    queryFn: () => jobDescriptions.list(),
  });

  const selectedStudent = studentList?.find((u: User) => String(u.id) === studentId);
  const selectedJd = jdList?.find((jd: JobDescription) => String(jd.id) === jdId);
  const canSubmit = Boolean(selectedStudent && selectedJd && !isPending);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedStudent || !selectedJd) return;

    setIsPending(true);
    setError(null);
    setResult(null);

    try {
      const analysis = await gapAnalyses.create({
        student_email: selectedStudent.email,
        job_description_id: selectedJd.id,
      });
      setResult(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al analizar la brecha.");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <AppLayout activePage="Nueva evaluación" userRole="tutor" userName="Ana García">
      <div className="max-w-2xl mx-auto space-y-6 pb-12">
        {/* Form card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          <h2 className="text-lg font-bold text-[#1E293B] mb-6">Evaluación de brecha</h2>
          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Student dropdown */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Estudiante</label>
              <Select value={studentId} onValueChange={setStudentId}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccioná un estudiante" />
                </SelectTrigger>
                <SelectContent>
                  {(studentList ?? []).map((u: User) => (
                    <SelectItem key={u.id} value={String(u.id)}>
                      {u.first_name} {u.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* JD dropdown */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Puesto</label>
              <Select value={jdId} onValueChange={setJdId}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccioná un puesto" />
                </SelectTrigger>
                <SelectContent>
                  {(jdList ?? []).map((jd: JobDescription) => (
                    <SelectItem key={jd.id} value={String(jd.id)}>
                      {jd.title} — {jd.posted_by.first_name} {jd.posted_by.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 rounded-xl p-3">{error}</div>
            )}

            <Button
              type="submit"
              disabled={!canSubmit}
              className="w-full bg-[#4F46E5] hover:bg-indigo-700 disabled:opacity-50"
            >
              {isPending ? "Analizando..." : "Analizar brecha"}
            </Button>
          </form>
        </div>

        {/* Result card */}
        {result && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-4">
            <div className="flex items-center gap-4">
              <div className="text-4xl font-bold text-[#4F46E5]">
                {result.gap_analysis.readiness_score}%
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
                  Puntaje de preparación
                </div>
                <div className="text-sm text-slate-600 mt-1">{result.gap_analysis.summary}</div>
              </div>
            </div>

            <div className="text-sm text-emerald-700 bg-emerald-50 rounded-xl p-3">
              Plan de aprendizaje generado (ID: {result.learning_path.id})
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-xs uppercase tracking-wider text-[#64748B] font-bold">
                    <th className="p-3">Habilidad</th>
                    <th className="p-3">Nivel actual</th>
                    <th className="p-3">Nivel requerido</th>
                    <th className="p-3">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.gap_analysis.gap_report.skills.map((skill) => (
                    <tr key={skill.name}>
                      <td className="p-3 font-medium text-[#1E293B]">{skill.name}</td>
                      <td className="p-3 text-slate-500">{skill.current_level}</td>
                      <td className="p-3 text-slate-500">{skill.required_level}</td>
                      <td className="p-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase ${STATUS_COLORS[skill.status] ?? "bg-slate-100 text-slate-500"}`}
                        >
                          {STATUS_LABELS[skill.status] ?? skill.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: only the pre-existing `ListadoPuestosEvaluacion.tsx` error. No other errors.
