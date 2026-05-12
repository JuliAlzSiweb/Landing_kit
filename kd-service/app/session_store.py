"""
Gestion de la sesion DWR (cookies extraidas a mano del navegador).

En la Fase 1 las cookies viven en un cookies.json y se cargan al arrancar
el proceso. Cuando el portal devuelve "Se ha perdido la sesion", marcamos
la sesion como invalida y devolvemos 503; el operador (o un job) tiene que
regenerar el cookies.json y llamar a POST /admin/reload-session.

En la Fase 2 esto se sustituira por un modulo `auth.py` con Playwright que
loguee con el .p12 y refresque cookies automaticamente.
"""

from __future__ import annotations

import threading
from pathlib import Path

from .elegibilidad import DWRSession


class SessionUnavailable(Exception):
    """No hay cookies validas cargadas."""


class _SessionStore:
    """
    Singleton thread-safe que mantiene la DWRSession actual en memoria.

    No es persistente: si el proceso reinicia, hay que recargar.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session: DWRSession | None = None
        self._cookies_path: Path | None = None
        self._invalidation_reason: str = ""

    def load_from_file(self, path: Path) -> DWRSession:
        """Carga (o recarga) las cookies desde disco."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"cookies.json no encontrado en {path}")
        with self._lock:
            session = DWRSession.from_file(str(path))
            self._session = session
            self._cookies_path = path
            self._invalidation_reason = ""
        return session

    def get(self) -> DWRSession:
        """Devuelve la sesion actual o lanza SessionUnavailable."""
        with self._lock:
            if self._session is None:
                raise SessionUnavailable(
                    self._invalidation_reason
                    or "Sesion no inicializada (falta cookies.json)"
                )
            return self._session

    def invalidate(self, reason: str) -> None:
        """Marca la sesion actual como invalida (p.ej. tras SessionExpired)."""
        with self._lock:
            self._session = None
            self._invalidation_reason = reason

    @property
    def cookies_path(self) -> Path | None:
        return self._cookies_path

    @property
    def is_loaded(self) -> bool:
        return self._session is not None


# Singleton de modulo
session_store = _SessionStore()
