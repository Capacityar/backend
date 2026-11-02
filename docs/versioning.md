# Política de versionado — backend

Esta política aplica la sección 9 de la guía de contribución de la organización ([`CONTRIBUTING.md`](https://github.com/Capacityar/.github/blob/main/CONTRIBUTING.md)) al backend. Si las dos difieren, manda `CONTRIBUTING.md`.

## Formato

Las versiones siguen [SemVer 2.0.0](https://semver.org/lang/es/): `vMAJOR.MINOR.PATCH`.

| Número | Cuándo sube | Ejemplo en el backend |
|--------|-------------|-----------------------|
| **MAJOR** | Cambio incompatible: un cliente que funcionaba deja de funcionar | Renombrar o quitar un endpoint (`/api/attempts` → `/api/exercise-attempts`), cambiar el formato de `GapReport`, hacer obligatorio un campo que antes era opcional |
| **MINOR** | Funcionalidad nueva compatible | Agregar un endpoint (`GET /api/metrics`), un módulo nuevo (`events`, `alerts`), una tabla nueva con su migración de Alembic |
| **PATCH** | Corrección compatible | Arreglar un bug, corregir `render.yaml` o el `Dockerfile`, mejorar un mensaje de error, actualizar documentación |

### Mientras estemos en `0.x.y`

El proyecto está en desarrollo: la API y el esquema pueden cambiar sin aviso. Por eso, mientras `MAJOR` sea `0`:

- **Cada línea base de sprint sube MINOR** (`v0.5.0` → `v0.6.0`), siguiendo el plan de sprints.
- Un cambio incompatible **no** obliga a pasar a `v1.0.0`, pero se anota en el `CHANGELOG.md` como incompatible.
- `v1.0.0` se marca cuando haya una versión productiva con usuarios reales y compatibilidad comprometida.

## Líneas base planificadas

Según el [plan de sprints v2](https://github.com/Capacityar/.github/blob/main/docs/plan-de-sprints-v2.md):

| Sprint | Línea base |
|--------|------------|
| Sprint 1 — Gestión de configuración | `v0.5.0` |
| Sprint 2 — Calidad del software | `v0.6.0` |
| Sprint 3 — Diseño centrado en el usuario | `v0.7.0` |
| Sprint 4 — Integración controlada | `v0.8.0` |
| Sprint 5 — Modelos de calidad y SQA | `v0.9.0` |
| Sprint 6 — Tiempo real e HMI | `v0.10.0` |

`v0.4.0-stable` (Sprint 0) quedó planificada pero no se creó: la numeración arranca en `v0.5.0`.

Los arreglos que se publiquen entre dos líneas base usan PATCH (`v0.5.1`, `v0.5.2`…).

## Tags

- Se usan **tags anotados** (`git tag -a`), que guardan autor, fecha y mensaje.
- El tag se crea **sobre `main`, después del merge**. Nunca sobre una rama de trabajo.
- Lo crea el responsable de la tarea de línea base (E2), no cada autor de PR.
- **Un tag no se mueve ni se borra.** Si una versión salió mal, se publica otra con PATCH+1.
- Backend y frontend comparten el número de línea base de cada sprint (`v0.5.0` en los dos repos), aunque después cada uno puede publicar sus PATCH por separado.

### Cómo crear una línea base

```bash
git switch main
git pull
git tag -a v0.5.0 -m "Línea base Sprint 1 — Gestión de configuración"
git push origin v0.5.0
```

Antes de crearlo, verificar que `CHANGELOG.md` en `main` describe lo que incluye esa versión.

## Registro de cambios

Cada versión se documenta en [`CHANGELOG.md`](../CHANGELOG.md), en la raíz del repo: qué incluye, qué se agregó, qué se corrigió y qué queda pendiente.
