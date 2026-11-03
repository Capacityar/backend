# auth helpers – versión mock (headers) y futura JWT
"""Módulo de autorización mínima.

- **Mock**: lee los headers ``X-User-Id`` y ``X-User-Role``
  (sólo para el sprint 6A).
- **JWT**: en la fase 6B se sustituirá la función ``get_user_from_headers``
  por ``get_user_from_jwt`` sin tocar los routers.
- **require_role**: decorador de dependencia que verifica que el rol del
  usuario esté dentro de los permitidos.

Este archivo sigue estrictamente el patrón *router / service / repository* del
proyecto: solo contiene funciones auxiliares y no introduce clases ni capas
intermedias.
"""

from fastapi import Header, HTTPException, Depends
from typing import Callable, Dict

User = Dict[str, str]  # {"id": "...", "role": "..."}

# ------------------------------------------------------------------
# 1️⃣ Mock – obtiene el usuario a partir de headers (uso en MVP)
def get_user_from_headers(
    x_user_id: int = Header(..., alias="X-User-Id"),
    x_user_role: str = Header(..., alias="X-User-Role"),
) -> User:
    """Devuelve un diccionario con ``id`` y ``role``.

    Los valores provienen de los headers enviados por el cliente. En la fase
    6B esta función será sustituida por la decodificación de un JWT.
    """
    return {"id": str(x_user_id), "role": x_user_role.lower()}

# ------------------------------------------------------------------
# 2️⃣ JWT – placeholder para la fase 6B (se implementará cuando sea necesario)
def get_user_from_jwt(token: str = Header(..., alias="Authorization")) -> User:  # pragma: no cover
    """Decodifica un JWT y devuelve ``id`` y ``role``.

    Esta función está declarada ahora para que la migración a JWT requiera
    únicamente cambiar el extractor usado por ``require_role``.
    """
    raise NotImplementedError("JWT decoder pendiente de implementar")

# ------------------------------------------------------------------
def require_role(*allowed: str, user_extractor: Callable = get_user_from_headers):
    """Dependencia que verifica que el rol del usuario esté autorizado.

    ``allowed`` es la lista de roles permitidos (p. ej. ``"student", "admin"``).
    ``user_extractor`` permite intercambiar la estrategia de obtención del
    usuario (headers → JWT) sin tocar los routers.
    """
    allowed_set = {r.lower() for r in allowed}

    def _checker(user: User = Depends(user_extractor)) -> User:
        if user["role"] not in allowed_set:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _checker
