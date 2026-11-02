# User Context & API-backed Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the logged-in user in a React context after login validates the email against the real API, and wire `MisHabilidades.tsx` to use that email instead of a hardcoded constant.

**Architecture:** New `UserContext` wraps the app (alongside the existing `LearningPathProvider`); `Login.tsx` calls `users.list()`, finds the user by email, sets context, and navigates by role; `MisHabilidades.tsx` reads email from context with `enabled: !!email` guard. No backend changes — password check is intentionally skipped for now.

**Tech Stack:** React context / TypeScript / TanStack Query / Wouter

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `frontend/src/context/UserContext.tsx` | `currentUser: User \| null` state + `useUser()` hook |
| Modify | `frontend/src/App.tsx` | Wrap app with `<UserProvider>` |
| Modify | `frontend/src/pages/Login.tsx` | API lookup by email, set context, navigate by role |
| Modify | `frontend/src/pages/MisHabilidades.tsx` | Replace hardcoded email with `useUser().currentUser?.email` |

---

### Task 1: Create `UserContext.tsx`

**Files:**
- Create: `frontend/src/context/UserContext.tsx`

- [ ] **Step 1: Create the file**

```tsx
import React, { createContext, useContext, useState, ReactNode } from "react";
import type { User } from "@/lib/api";

interface UserContextType {
  currentUser: User | null;
  setCurrentUser: (user: User | null) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  return (
    <UserContext.Provider value={{ currentUser, setCurrentUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextType {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no new errors.

---

### Task 2: Wrap app with `UserProvider` in `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

The current wrapper order is `QueryClientProvider > TooltipProvider > LearningPathProvider > WouterRouter`. Add `UserProvider` just inside `QueryClientProvider` so it's available to everything below.

- [ ] **Step 1: Add the import**

Add after the existing context imports:

```typescript
import { UserProvider } from "@/context/UserContext";
```

- [ ] **Step 2: Wrap the children**

Replace the `App` function body so it reads:

```tsx
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <UserProvider>
        <TooltipProvider>
          <LearningPathProvider>
            <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
              <Router />
            </WouterRouter>
          </LearningPathProvider>
          <Toaster />
        </TooltipProvider>
      </UserProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no new errors.

---

### Task 3: Replace `Login.tsx` with API-backed version

**Files:**
- Modify: `frontend/src/pages/Login.tsx`

Key changes from the current version:
- Remove `CREDENTIALS` (had hardcoded password + path). Replace with `DEMO_EMAILS` (email + label only).
- Add `ROLE_PATHS` map (`student→/student`, `tutor→/tutor`, `company_admin→/companies`, `admin→/student`).
- `handleSubmit` becomes async: calls `users.list()`, finds matching email, sets context, navigates.
- Password field stays visible but is not checked.
- Import `useUser` and `users` from their respective modules.

- [ ] **Step 1: Replace the entire file**

```tsx
import React, { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { users } from "@/lib/api";
import { useUser } from "@/context/UserContext";

type UserType = "student" | "tutor" | "company";

const DEMO_EMAILS: Record<UserType, { email: string; label: string }> = {
  student: { email: "estudiante@demo.com", label: "Estudiante" },
  tutor:   { email: "tutor@demo.com",      label: "Tutor"      },
  company: { email: "empresa@demo.com",    label: "Empresa"    },
};

const ROLE_PATHS: Record<string, string> = {
  student:       "/student",
  tutor:         "/tutor",
  company_admin: "/companies",
  admin:         "/student",
};

export function Login() {
  const [, navigate] = useLocation();
  const { setCurrentUser } = useUser();
  const [userType, setUserType] = useState<UserType>("student");
  const [email, setEmail] = useState(DEMO_EMAILS.student.email);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  function handleTypeChange(type: UserType) {
    setUserType(type);
    setEmail(DEMO_EMAILS[type].email);
    setError("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const allUsers = await users.list();
      const found = allUsers.find((u) => u.email === email.trim());
      if (!found) {
        setError("Usuario no encontrado.");
        return;
      }
      setCurrentUser(found);
      navigate(ROLE_PATHS[found.role] ?? "/student");
    } catch {
      setError("Error al conectar con el servidor.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-[#4F46E5] mb-2 tracking-tight">CapacitaYa</h1>
        <p className="text-slate-500 mb-6">Ingresá para continuar</p>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Selector de tipo */}
          <div className="flex gap-2">
            {(Object.entries(DEMO_EMAILS) as [UserType, { email: string; label: string }][]).map(
              ([type, { label }]) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeChange(type)}
                  className={`flex-1 py-2 rounded-lg border text-sm font-medium transition-colors ${
                    userType === type
                      ? "bg-[#4F46E5] text-white border-[#4F46E5]"
                      : "bg-white text-slate-600 border-slate-200 hover:border-[#4F46E5]"
                  }`}
                >
                  {label}
                </button>
              )
            )}
          </div>

          {/* Email */}
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>

          {/* Contraseña — ignorada por ahora */}
          <div className="space-y-1.5">
            <Label htmlFor="password">Contraseña</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <Button
            type="submit"
            disabled={isLoading}
            className="w-full bg-[#4F46E5] hover:bg-[#4338CA]"
          >
            {isLoading ? "Verificando..." : "Ingresar"}
          </Button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/dev/capacitaya/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no new errors.

---

### Task 4: Wire `MisHabilidades.tsx` to use context email

**Files:**
- Modify: `frontend/src/pages/MisHabilidades.tsx`

Remove the hardcoded `STUDENT_EMAIL` constant. Import `useUser`. Guard all API calls with `enabled: !!email` or early returns.

- [ ] **Step 1: Replace the entire file**

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
import { useUser } from "@/context/UserContext";

export function MisHabilidades() {
  const { toast } = useToast();
  const { currentUser } = useUser();
  const email = currentUser?.email ?? null;

  const [mySkills, setMySkills] = useState<UserSkill[]>([]);
  const [skillQuery, setSkillQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Skill[]>([]);

  const { data: initialSkills } = useQuery({
    queryKey: ["user-skills", email],
    queryFn: () => userSkills.list(email!),
    enabled: !!email,
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
    if (!email) return;
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
      const added = await userSkills.add(email, {
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
    if (!email) return;
    try {
      await userSkills.remove(email, skillId);
      setMySkills((prev) => prev.filter((s) => s.skill_id !== skillId));
    } catch {
      toast({ title: "Error al eliminar skill", variant: "destructive" });
    }
  };

  const updateLevel = async (skill: UserSkill, level: SkillLevel) => {
    if (!email) return;
    try {
      await userSkills.remove(email, skill.skill_id);
      const updated = await userSkills.add(email, {
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

  if (!email) {
    return (
      <AppLayout activePage="Mis Habilidades" userRole="student" userName="Estudiante">
        <div className="text-center text-slate-400 py-12">
          No estás logueado.
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout activePage="Mis Habilidades" userRole="student" userName={`${currentUser!.first_name} ${currentUser!.last_name}`}>
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

Expected: no new errors.
