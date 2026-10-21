# Tutor Gap Analysis Form Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Nueva evaluación" button to `ListadoPuestosEvaluacion` that routes to a new `/tutor/gap-analysis` page with dropdowns for student and job description and two PDF uploads that call the existing `POST /api/gap-analyses` endpoint.

**Architecture:** Four frontend-only changes — extend `api.ts` with gap analysis types and a multipart fetch helper, create the new page component with controlled form state and inline result display, add the button to the existing list page, and register the route. No backend changes — the endpoint already exists.

**Tech Stack:** React 18 / TypeScript / TanStack Query / Wouter / Tailwind CSS / shadcn Select + Button

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Modify | `frontend/src/lib/api.ts` | Add `GapSkill`, `GapReport`, `GapAnalysis` types + `gapAnalyses.create()` |
| Create | `frontend/src/pages/TutorGapAnalysis.tsx` | Form page: student dropdown, JD dropdown, two PDF uploads, result display |
| Modify | `frontend/src/pages/ListadoPuestosEvaluacion.tsx` | Add "Nueva evaluación" button linking to `/tutor/gap-analysis` |
| Modify | `frontend/src/App.tsx` | Register `/tutor/gap-analysis` route |

---

### Task 1: Extend `api.ts` with gap analysis types and client

**Files:**
- Modify: `frontend/src/lib/api.ts`

The existing `POST /api/gap-analyses` accepts multipart/form-data (not JSON), so we cannot reuse the `request()` helper that always sets `Content-Type: application/json`. We do a raw `fetch` instead.

- [ ] **Step 1: Add types and `gapAnalyses` client at the end of `frontend/src/lib/api.ts`**

Append the following block **after** the last `export const jobDescriptions = { ... };` block:

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

export const gapAnalyses = {
  create: async (formData: FormData): Promise<GapAnalysis> => {
    const res = await fetch("/api/gap-analyses", {
      method: "POST",
      body: formData,
      // No Content-Type header — browser sets multipart/form-data with boundary automatically
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${detail}`);
    }
    return res.json() as Promise<GapAnalysis>;
  },
};
```

Note: `SkillPriority` and `SkillStatus` are already defined earlier in `api.ts` as `"HIGH" | "MEDIUM" | "LOW"` and `"READY" | "NEEDS_WORK" | "MISSING"` respectively.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

---

### Task 2: Create `TutorGapAnalysis.tsx`

**Files:**
- Create: `frontend/src/pages/TutorGapAnalysis.tsx`

- [ ] **Step 1: Create the file**

```tsx
import React, { useRef, useState } from "react";
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
import { Upload } from "lucide-react";
import {
  GapAnalysis,
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
  const [studentDoc, setStudentDoc] = useState<File | null>(null);
  const [positionDoc, setPositionDoc] = useState<File | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [result, setResult] = useState<GapAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  const studentDocRef = useRef<HTMLInputElement>(null);
  const positionDocRef = useRef<HTMLInputElement>(null);

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
  const canSubmit = Boolean(selectedStudent && selectedJd && studentDoc && positionDoc && !isPending);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedStudent || !selectedJd || !studentDoc || !positionDoc) return;

    setIsPending(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("student_email", selectedStudent.email);
      formData.append("company_email", selectedJd.posted_by.email);
      formData.append("student_doc", studentDoc);
      formData.append("position_doc", positionDoc);

      const analysis = await gapAnalyses.create(formData);
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

            {/* Student CV upload */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">CV del estudiante (PDF)</label>
              <div
                className="border-2 border-dashed border-slate-200 rounded-xl p-4 flex items-center gap-3 cursor-pointer hover:border-indigo-300 transition-colors"
                onClick={() => studentDocRef.current?.click()}
              >
                <Upload className="w-5 h-5 text-slate-400 shrink-0" />
                <span className="text-sm text-slate-500">
                  {studentDoc ? studentDoc.name : "Hacé clic para subir el CV"}
                </span>
              </div>
              <input
                ref={studentDocRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => setStudentDoc(e.target.files?.[0] ?? null)}
              />
            </div>

            {/* Position doc upload */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Documento del puesto (PDF)</label>
              <div
                className="border-2 border-dashed border-slate-200 rounded-xl p-4 flex items-center gap-3 cursor-pointer hover:border-indigo-300 transition-colors"
                onClick={() => positionDocRef.current?.click()}
              >
                <Upload className="w-5 h-5 text-slate-400 shrink-0" />
                <span className="text-sm text-slate-500">
                  {positionDoc ? positionDoc.name : "Hacé clic para subir el documento del puesto"}
                </span>
              </div>
              <input
                ref={positionDocRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => setPositionDoc(e.target.files?.[0] ?? null)}
              />
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
              <div className="text-4xl font-bold text-[#4F46E5]">{result.readiness_score}%</div>
              <div>
                <div className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
                  Puntaje de preparación
                </div>
                <div className="text-sm text-slate-600 mt-1">{result.summary}</div>
              </div>
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
                  {result.gap_report.skills.map((skill) => (
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

Expected: no errors.

---

### Task 3: Add "Nueva evaluación" button to `ListadoPuestosEvaluacion.tsx`

**Files:**
- Modify: `frontend/src/pages/ListadoPuestosEvaluacion.tsx`

Currently the top bar only has the province `<Select>`. We add a `<Link>` + `<Button>` on the right side, matching the pattern used in `ListadoPuestos.tsx`.

- [ ] **Step 1: Add `Link` import and button**

The file currently imports `{ Link }` from `"wouter"` — check first. If it's missing, add it.

Add `Plus` to the lucide imports (it's already importing `MapPin, Plus, User` — `Plus` is there, skip if already present). Actually, for this button we'll use a different icon or no icon. Use just a text button labeled "Nueva evaluación".

Replace the top `<div className="flex items-center justify-between gap-4">` block. The current block is:

```tsx
        <div className="flex items-center justify-between gap-4">
          <div className="w-64">
            <Select value={province} onValueChange={setProvince}>
              <SelectTrigger>
                <SelectValue placeholder="Todas las provincias" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Todas las provincias</SelectItem>
                {ARGENTINIAN_PROVINCES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
```

Replace it with:

```tsx
        <div className="flex items-center justify-between gap-4">
          <div className="w-64">
            <Select value={province} onValueChange={setProvince}>
              <SelectTrigger>
                <SelectValue placeholder="Todas las provincias" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Todas las provincias</SelectItem>
                {ARGENTINIAN_PROVINCES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Link href="/tutor/gap-analysis">
            <Button className="bg-[#4F46E5] hover:bg-indigo-700">
              Nueva evaluación
            </Button>
          </Link>
        </div>
```

Also make sure `Link` is imported from `"wouter"` and `Button` is imported from `"@/components/ui/button"` — both should already be in the file, verify before saving.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

---

### Task 4: Register `/tutor/gap-analysis` route in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add import**

After the `TutorCompanias` import line, add:

```typescript
import { TutorGapAnalysis } from "@/pages/TutorGapAnalysis";
```

- [ ] **Step 2: Add route**

After `<Route path="/tutor/companies" component={TutorCompanias} />`, add:

```tsx
<Route path="/tutor/gap-analysis" component={TutorGapAnalysis} />
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.
