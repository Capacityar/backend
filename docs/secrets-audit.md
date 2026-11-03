# Auditoría de variables de entorno y secretos (S5.3)

Unidad IV — integridad y responsabilidad. Inventario de todas las variables de
entorno del backend, identificación de secretos, verificación de que no haya
claves reales en el repo y política de rotación.

Fuente de verdad del inventario: `app/config.py` (clase `Settings`) +
`app/modules/auth/service.py` (JWT, lee `os.getenv` directo).

## 1. Inventario

**Secreto** = su filtración compromete datos o permite suplantación. Nunca se
commitea su valor real; en el repo solo van placeholders (`.env.example`).

| Variable | Origen | Secreto | Default | Descripción |
|---|---|:--:|---|---|
| `APP_NAME` | `Settings.app_name` | no | `Capacity AR API` | Nombre de la app |
| `APP_ENV` | `Settings.app_env` | no | `local` | `local` \| `production` |
| `APP_DEBUG` | `Settings.app_debug` | no | `False` | Debug flag |
| `DATABASE_URL` | `Settings.database_url` | **sí** | postgres local | Credenciales de BD (usuario:password@host) |
| `PLAN_GENERATOR` | `Settings.plan_generator` | no | `mock` | `mock` \| `groq` \| `gemini` |
| `LLM_TIMEOUT_SECONDS` | `Settings.llm_timeout_seconds` | no | `30.0` | Timeout de llamadas a IA |
| `GROQ_API_KEY` | `Settings.groq_api_key` | **sí** | `None` | Clave del LLM Groq |
| `GROQ_MODEL` | `Settings.groq_model` | no | `llama-3.3-70b-versatile` | Modelo Groq |
| `GEMINI_API_KEY` | `Settings.gemini_api_key` | **sí** | `None` | Clave del LLM Gemini |
| `GEMINI_MODEL` | `Settings.gemini_model` | no | `gemini-2.0-flash` | Modelo Gemini |
| `API_TARGET` | `Settings.api_target` | no | `/api` | Prefijo de routing |
| `CORS_ORIGINS` | `Settings.cors_origins` | no | localhost + vercel | Orígenes permitidos (coma) |
| `JWT_SECRET_KEY` | `auth/service.py` (os.getenv) | **sí** | `insecure-secret-key` ⚠️ | Clave de firma de JWT — ver H1 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `auth/service.py` (os.getenv) | no | `30` | TTL access token (min) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `auth/service.py` (os.getenv) | no | `7` | TTL refresh token (días) |

Todas están documentadas en `.env.example` con placeholders.

## 2. Secretos identificados (4)

1. `DATABASE_URL` — credenciales de la base (Neon/Postgres).
2. `GROQ_API_KEY` — clave del proveedor LLM.
3. `GEMINI_API_KEY` — clave del proveedor LLM.
4. `JWT_SECRET_KEY` — clave de firma de tokens (agregada en S2.1; el issue
   original listaba 3, este es el cuarto).

## 3. Escaneo de claves hardcodeadas

```bash
grep -rEn "(sk-[A-Za-z0-9]|gsk_|your_.*_here)" app/ --exclude-dir=__pycache__
# → sin resultados: ninguna clave real embebida ✅
```

No hay API keys reales en el código. Todas se leen de entorno
(`settings.groq_api_key`, `settings.gemini_api_key`, `os.getenv(...)`).

## 4. Hallazgos

### H1 (alto) — Default inseguro de `JWT_SECRET_KEY`

`app/modules/auth/service.py:13`:

```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insecure-secret-key")
```

Si producción no setea `JWT_SECRET_KEY`, los tokens se firman con una clave
pública y conocida → **cualquiera puede falsificar un JWT válido** y suplantar
usuarios. El default enmascara el error (la app arranca igual) en vez de fallar.

**Recomendación:** fail-closed — sin default (o default solo cuando
`app_env == "local"`), y abortar el arranque si falta en `production`. No se
corrige en este PR porque toca el módulo `auth/` (S2.1, de otro equipo, recién
mergeado); se deja como ticket aparte para coordinar. Mitigación inmediata:
setear un `JWT_SECRET_KEY` fuerte en Render → Environment ya.

### H2 (medio) — Config de JWT fuera de `Settings`

Las 3 variables de JWT se leen con `os.getenv` directo en `auth/service.py`, no
por `Settings`. Rompe la fuente única de verdad (inventario/validación/tipado) y
fue lo que dejó esas vars sin aparecer en `config.py`.

**Recomendación:** moverlas a `Settings` (`jwt_secret_key`, etc.) y consumir
`settings.*`. También coordinación con el dueño de `auth/`.

## 5. Política de rotación de secretos

Los secretos viven en **Render → Environment** (prod) y en `.env` local (nunca
commiteado — está en `.gitignore`). Rotar significa reemplazar el valor en el
proveedor y en Render; nunca en el repo.

| Secreto | Cómo rotar |
|---|---|
| `DATABASE_URL` | En Neon: *Roles* → resetear password del rol (o crear rol nuevo y borrar el viejo). Copiar la nueva connection string a Render → Environment. Render redeploya solo. |
| `GROQ_API_KEY` | En console.groq.com → *API Keys*: crear key nueva, actualizar Render, borrar la vieja. |
| `GEMINI_API_KEY` | En Google AI Studio / Cloud Console → *API Keys*: regenerar, actualizar Render, revocar la anterior. |
| `JWT_SECRET_KEY` | Generar uno nuevo (`python -c "import secrets; print(secrets.token_urlsafe(48))"`), setear en Render. **Efecto:** invalida todos los tokens emitidos → los usuarios deben re-loguearse (aceptable; es el comportamiento esperado de una rotación de firma). |

**Cuándo rotar:** ante sospecha de filtración, salida de un miembro con acceso,
o de forma preventiva cada ~90 días. Tras rotar, verificar que no quedó el valor
viejo en logs, historial de shell ni en el board.

**Reglas generales:**
- Nunca commitear un `.env` ni pegar un secreto en issues/PRs/chat.
- `.env.example` solo lleva placeholders (`your_*_here`, credenciales dummy).
- Un secreto que estuvo en un commit se considera comprometido aunque se borre
  después (queda en el historial de git) → rotarlo.
