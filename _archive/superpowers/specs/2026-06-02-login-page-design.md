# Login Page — Diseño

**Fecha:** 2026-06-02  
**Scope:** Frontend únicamente. Sin cambios en el backend.

## Objetivo

Agregar una pantalla de login en `/login` que permita seleccionar un rol de demo (Estudiante / Tutor / Empresa), auto-rellenar las credenciales del rol, validarlas contra valores hardcodeados y navegar a la sección correspondiente.

## Rutas

| Ruta | Componente | Notas |
|---|---|---|
| `/login` | `Login` (nuevo) | Pantalla de login |
| `/student` | `Dashboard` (existente) | Vista del estudiante/candidato |
| `/tutor` | `PanelTutor` (existente) | Vista del tutor |
| `/companies` | `ListadoPuestos` (existente) | Vista de empresa |

Las rutas existentes (`/`, `/panel-tutor`, `/companies/jobs`, etc.) no se modifican.

## Componente Login (`frontend/src/pages/Login.tsx`)

### Comportamiento

1. Selector de tipo de usuario: 3 botones tipo tab — **Estudiante**, **Tutor**, **Empresa**.
2. Al seleccionar un tipo, el campo email se auto-rellena con la credencial del rol.
3. El usuario puede editar el email manualmente (permite probar credenciales incorrectas).
4. Campo password (type="password").
5. Al hacer click en "Ingresar":
   - Si `email === credencial_del_rol && password === "demo"` → `navigate(destino)`.
   - Si no coincide → mensaje de error inline debajo del formulario.

### Credenciales hardcodeadas

```ts
const CREDENTIALS = {
  student: { email: "estudiante@demo.com", path: "/student" },
  tutor:   { email: "tutor@demo.com",      path: "/tutor" },
  company: { email: "empresa@demo.com",    path: "/companies" },
} as const;

const PASSWORD = "demo";
```

### Validación

- El email debe coincidir exactamente con el del rol seleccionado.
- La contraseña debe ser `"demo"`.
- Si falla: mostrar `"Credenciales incorrectas."` debajo del botón.
- No hay intentos limitados ni bloqueos (es demo).

### UI / Estilo

- Pantalla completa (`min-h-screen`) con fondo `#F8FAFC` (igual que el app).
- Card centrada (max-w-md), bordes redondeados, shadow-sm.
- Header: logo "CapacitaYa" en `#4F46E5`.
- Selector de tipo: 3 botones con borde, el seleccionado con fondo `#4F46E5` y texto blanco.
- Inputs estándar del proyecto (componente `Input` de `@/components/ui/input`).
- Botón submit: `Button` primario indigo, ancho completo.
- Sin sidebar ni AppLayout — es la única pantalla fuera del layout.

## Cambios en `App.tsx`

Agregar 4 rutas al `<Switch>`:

```tsx
<Route path="/login" component={Login} />
<Route path="/student" component={Dashboard} />
<Route path="/tutor" component={PanelTutor} />
<Route path="/companies" component={ListadoPuestos} />
```

## Lo que NO se hace

- Sin protección de rutas (las rutas destino son accesibles directo sin login).
- Sin estado de auth (context, localStorage, sessionStorage).
- Sin integración con el backend.
- Sin animaciones de transición.
