# Login Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una pantalla de login en `/login` con selector de rol demo que redirige a `/student`, `/tutor` o `/companies`.

**Architecture:** Un componente `Login.tsx` autocontenido con estado local (React hooks). No hay contexto ni storage — la validación es inline con credenciales hardcodeadas y la navegación usa el hook `useLocation` de wouter. Se agregan 4 rutas nuevas en `App.tsx`.

**Tech Stack:** React 19, TypeScript, wouter (routing), Tailwind CSS, shadcn/ui (`Input`, `Label`, `Button`)

---

## Archivos

| Acción | Ruta |
|--------|------|
| Crear | `frontend/src/pages/Login.tsx` |
| Modificar | `frontend/src/App.tsx` |

> No hay suite de tests configurada en el proyecto (ver `CLAUDE.md`). Las tareas no incluyen pasos de TDD.

---

### Tarea 1: Componente Login

**Archivos:**
- Crear: `frontend/src/pages/Login.tsx`

- [ ] **Paso 1: Crear el archivo con tipos y credenciales**

```tsx
// frontend/src/pages/Login.tsx
import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type UserType = "student" | "tutor" | "company";

const CREDENTIALS: Record<UserType, { email: string; path: string; label: string }> = {
  student: { email: "estudiante@demo.com", path: "/student",   label: "Estudiante" },
  tutor:   { email: "tutor@demo.com",      path: "/tutor",     label: "Tutor"      },
  company: { email: "empresa@demo.com",    path: "/companies", label: "Empresa"    },
};

const PASSWORD = "demo";
```

- [ ] **Paso 2: Agregar el componente con estado y handlers**

Continuar en el mismo archivo, debajo de las constantes:

```tsx
export function Login() {
  const [, navigate] = useLocation();
  const [userType, setUserType] = useState<UserType>("student");
  const [email, setEmail] = useState(CREDENTIALS.student.email);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleTypeChange(type: UserType) {
    setUserType(type);
    setEmail(CREDENTIALS[type].email);
    setError("");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cred = CREDENTIALS[userType];
    if (email === cred.email && password === PASSWORD) {
      navigate(cred.path);
    } else {
      setError("Credenciales incorrectas.");
    }
  }
```

- [ ] **Paso 3: Agregar el JSX del formulario**

Continuar en el mismo archivo, cerrando el componente:

```tsx
  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-[#4F46E5] mb-2 tracking-tight">CapacitaYa</h1>
        <p className="text-slate-500 mb-6">Ingresá para continuar</p>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Selector de tipo */}
          <div className="flex gap-2">
            {(Object.entries(CREDENTIALS) as [UserType, { email: string; path: string; label: string }][]).map(
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

          {/* Contraseña */}
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

          <Button type="submit" className="w-full bg-[#4F46E5] hover:bg-[#4338CA]">
            Ingresar
          </Button>
        </form>
      </div>
    </div>
  );
}
```

---

### Tarea 2: Registrar rutas en App.tsx

**Archivos:**
- Modificar: `frontend/src/App.tsx`

- [ ] **Paso 1: Agregar el import de Login**

En `frontend/src/App.tsx`, después de la línea `import { ListadoPuestos } from "@/pages/ListadoPuestos";`, agregar:

```tsx
import { Login } from "@/pages/Login";
```

- [ ] **Paso 2: Agregar las 4 rutas nuevas al Switch**

En el `<Switch>` de `Router()`, antes de `<Route component={NotFound} />`, agregar:

```tsx
<Route path="/login" component={Login} />
<Route path="/student" component={Dashboard} />
<Route path="/tutor" component={PanelTutor} />
<Route path="/companies" component={ListadoPuestos} />
```

El `Switch` completo debe quedar:

```tsx
<Switch>
  <Route path="/" component={Dashboard} />
  <Route path="/plan" component={PlanCapacitacion} />
  <Route path="/modulo" component={ModuloIA} />
  <Route path="/evaluacion" component={Evaluacion} />
  <Route path="/progreso" component={ProgresoyLogros} />
  <Route path="/canal-tutor" component={CanalTutor} />
  <Route path="/panel-tutor" component={PanelTutor} />
  <Route path="/detalle-candidato" component={DetalleCandidato} />
  <Route path="/demo-api" component={DemoApi} />
  <Route path="/companies/new-job" component={NuevoPuesto} />
  <Route path="/companies/jobs" component={ListadoPuestos} />
  <Route path="/login" component={Login} />
  <Route path="/student" component={Dashboard} />
  <Route path="/tutor" component={PanelTutor} />
  <Route path="/companies" component={ListadoPuestos} />
  <Route component={NotFound} />
</Switch>
```

---

### Tarea 3: Verificar en el navegador

- [ ] **Paso 1: Levantar el servidor de desarrollo**

```bash
cd frontend && npm run dev
```

- [ ] **Paso 2: Verificar flujo Estudiante**

  1. Ir a `http://localhost:5173/login`
  2. "Estudiante" debe estar seleccionado por defecto; email = `estudiante@demo.com`
  3. Ingresar password `demo` → debe navegar a `/student` (Dashboard)

- [ ] **Paso 3: Verificar flujo Tutor**

  1. Volver a `/login`
  2. Hacer click en "Tutor" → email cambia a `tutor@demo.com`
  3. Ingresar password `demo` → navega a `/tutor` (PanelTutor)

- [ ] **Paso 4: Verificar flujo Empresa**

  1. Volver a `/login`
  2. Hacer click en "Empresa" → email cambia a `empresa@demo.com`
  3. Ingresar password `demo` → navega a `/companies` (ListadoPuestos)

- [ ] **Paso 5: Verificar error de credenciales**

  1. Ir a `/login`, dejar el email de Estudiante
  2. Escribir password incorrecto (ej. `wrong`)
  3. Debe aparecer el mensaje `"Credenciales incorrectas."` sin navegar
