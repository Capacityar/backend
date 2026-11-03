# Resumen de cambios – Sprint **S2.1** (Backend)

## 1️⃣ Nuevo módulo de autorización
- **Archivo creado**: `backend-main/app/shared/auth.py`
- Contiene:
  - `get_user_from_headers` → lee los headers `X-User-Id` y `X-User-Role` (mock MVP).
  - `get_user_from_jwt` → *placeholder* para la fase 6B (JWT).
  - `require_role` → dependencia que verifica que el rol del usuario esté dentro de los permitidos.  Recibe opcionalmente el extractor de usuario, lo que permite cambiar de mock a JWT sin tocar los routers.
- Mantiene la **simplicidad** (≈ 30 líneas) y sigue el patrón *router / service / repository*.

## 2️⃣ Protección de endpoint
- **Archivo modificado**: `backend-main/app/modules/learning_paths/router.py`
  - Se añadió la importación: `from app.shared.auth import require_role`
  - Al endpoint **POST `/learning-paths/`** se le agregó la dependencia:
    ```python
    @router.post(
        "",
        response_model=StoredLearningPath,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_role("admin"))],
    )
    ```
  - Sólo el rol `admin` puede crear un learning‑path (ejemplo de aplicación de la matriz de accesos).

## 3️⃣ Dependencias nuevas en el proyecto
- **Archivo modificado**: `backend-main/requirements.txt`
  - Se añadieron:
    ```text
    fastapi
    python-jose[cryptography]
    passlib[bcrypt]
    ```
  - `python-jose` será usado para firmar/validar JWT en la fase 6B y `passlib[bcrypt]` para el hash de contraseñas.

## 4️⃣ Cómo funciona la migración a JWT (fase 6B)
1. Implementar la lógica dentro de `get_user_from_jwt` (decodificar con `python‑jose`).
2. Cambiar el extractor en los routers o, de forma global, redefinir `require_role` para usar `get_user_from_jwt`:
   ```python
   from app.shared.auth import require_role, get_user_from_jwt
   # Ejemplo global (se puede hacer en un solo lugar)
   require_role = lambda *r: require_role(*r, user_extractor=get_user_from_jwt)
   ```
3. No es necesario tocar nuevamente los routers; siguen usando `require_role`.

## 5️⃣ Próximos pasos sugeridos
- Aplicar `require_role` a los demás routers siguiendo **`docs/access-matrix.md`**.
- Implementar la función `get_user_from_jwt` y crear el módulo `auth/` con endpoints `register`, `login`, `refresh`.
- Añadir pruebas unitarias que verifiquen los códigos `401/403` según el rol.
- Actualizar la documentación (`docs/authentication.md`).

---
**Nota:** Se evitó cualquier sobre‑ingeniería; solo se añadió el archivo esencial y se modificó un endpoint como ejemplo, cumpliendo con el principio de *cambio mínimo*.


---

## 6️⃣ Fase 6B — JWT real (implementación completa)

### Archivos nuevos

| Archivo | Descripción |
|---------|-------------|
| pp/modules/auth/schemas.py | Modelos Pydantic: RegisterIn, LoginIn, TokenOut. |
| pp/modules/auth/service.py | Hash de contraseñas (passlib/bcrypt), registro, autenticación, generación y decodificación de JWT (python-jose). |
| pp/modules/auth/router.py | Endpoints POST /api/auth/register, POST /api/auth/login, POST /api/auth/refresh. |
| pp/modules/auth/__init__.py | Exporta outer para que main.py lo incluya. |
| 	ests/conftest.py | Fixture de cliente de pruebas con base de datos SQLite en memoria. |
| 	ests/auth/test_auth.py | 8 tests: registro, login y refresh (flujos válidos e inválidos). |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| pp/modules/users/models.py | Añadido campo password_hash: Mapped[str] al modelo User. |
| pp/modules/users/schemas.py | UserCreate incluye password_hash: str = "". |
| pp/main.py | Importa e incluye uth_router bajo el prefijo /api. |
| .env.example | Añadidas variables JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS. |

### Flujo de autenticación

`
POST /api/auth/register  →  { email, password, role }  →  { access_token, refresh_token }
POST /api/auth/login     →  { email, password }         →  { access_token, refresh_token }
POST /api/auth/refresh   →  { refresh_token }           →  { access_token, refresh_token }
`

- El **access token** expira en 30 minutos (configurable con ACCESS_TOKEN_EXPIRE_MINUTES).
- El **refresh token** expira en 7 días (configurable con REFRESH_TOKEN_EXPIRE_DAYS).
- Los tokens son **JWT auto-contenidos** (sin storage en base de datos); el refresh es simplemente un JWT de vida más larga.

### Variables de entorno requeridas

`env
JWT_SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
`

> **Nota**: El Sprint S2.1 queda completo. La función get_user_from_jwt en shared/auth.py ya puede ser usada como extractor en equire_role para proteger endpoints con JWT real.
