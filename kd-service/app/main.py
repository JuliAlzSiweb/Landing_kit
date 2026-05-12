"""
FastAPI app: expone kd_contract_parser por HTTP detras de X-API-Key.

Endpoints:
  GET  /health                  publico (para nginx / pm2 / monitor)
  POST /elegibilidad            requiere X-API-Key
  POST /admin/reload-session    requiere X-API-Key (recarga cookies.json)

El servicio escucha SOLO en loopback (127.0.0.1) y se asume que el unico
cliente legitimo es el backend Node de la landing. CORS por defecto vacio.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .api_models import (
    ElegibilidadRequest,
    ElegibilidadResponse,
    ErrorResponse,
    to_response,
)
from .elegibilidad import DWRError, SessionExpiredError, comprobar_elegibilidad
from .session_store import SessionUnavailable, session_store
from .settings import Settings, get_settings


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("kd-service")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-5s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Lifespan: cargar cookies al arrancar (no bloqueante si fallan)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _setup_logging(settings.LOG_LEVEL)
    logger.info("kd-service v%s arrancando en modo %s", __version__, settings.ENV)
    try:
        session_store.load_from_file(settings.COOKIES_PATH)
        logger.info("cookies.json cargado desde %s", settings.COOKIES_PATH)
    except FileNotFoundError as e:
        # No abortamos el arranque: el proceso queda vivo pero /elegibilidad
        # responde 503 hasta que se haga POST /admin/reload-session.
        logger.warning("Arrancando SIN cookies cargadas: %s", e)
    except Exception as e:
        logger.error("Fallo cargando cookies.json: %s", e)
    yield
    logger.info("kd-service apagandose")


app = FastAPI(
    title="kd-service",
    version=__version__,
    description="Wrapper HTTP del PoC kd_contract_parser para la landing Kit Digital.",
    lifespan=lifespan,
    # En produccion no exponemos /docs ni /redoc por loopback no es critico,
    # pero por higiene los desactivamos cuando ENV=production.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def _enable_docs_in_dev(request, call_next):
    """Activa /docs solo en development. No-op en produccion."""
    return await call_next(request)


# CORS: solo si hay origenes definidos (debug). En produccion vacio.
_settings_for_cors = get_settings()
if _settings_for_cors.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings_for_cors.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "session_loaded": session_store.is_loaded,
    }


@app.post(
    "/elegibilidad",
    response_model=ElegibilidadResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
def post_elegibilidad(
    payload: ElegibilidadRequest,
    _: None = Depends(require_api_key),
) -> ElegibilidadResponse:
    try:
        session = session_store.get()
    except SessionUnavailable as e:
        logger.warning("/elegibilidad sin sesion: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "session_unavailable",
                "message": str(e),
            },
        )

    try:
        resultado = comprobar_elegibilidad(
            session=session,
            nif=payload.nif.upper(),
            bono=payload.bono,
            categoria_preferida=payload.categoria,
        )
    except SessionExpiredError as e:
        # Marcamos la sesion como invalida y devolvemos 503: el operador
        # tendra que regenerar cookies.json y hacer reload.
        session_store.invalidate(f"Sesion expirada: {e}")
        logger.warning("Sesion DWR expirada, requiere recarga manual de cookies")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "session_expired",
                "message": (
                    "La sesion DWR contra el portal ha expirado. "
                    "Regenerar cookies.json y llamar a POST /admin/reload-session."
                ),
            },
        )
    except DWRError as e:
        logger.error("DWRError llamando al portal: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "upstream_error",
                "message": str(e),
            },
        )

    logger.info(
        "elegibilidad nif=%s bono=%s cat=%s eligible=%s ms=%d",
        payload.nif,
        payload.bono,
        payload.categoria,
        resultado.elegible,
        resultado.duracion_ms,
    )
    return to_response(resultado)


@app.post("/admin/reload-session")
def reload_session(
    _: None = Depends(require_api_key),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Releera cookies.json desde disco. Usar tras regenerar el fichero a mano
    cuando la sesion DWR haya expirado.
    """
    try:
        session = session_store.load_from_file(settings.COOKIES_PATH)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "cookies_not_found", "message": str(e)},
        )
    except Exception as e:
        logger.error("Error recargando cookies.json: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_cookies", "message": str(e)},
        )

    logger.info("cookies.json recargado correctamente desde %s", settings.COOKIES_PATH)
    return {
        "status": "ok",
        "message": "Sesion recargada",
        "window_name": session.window_name,
    }


# ---------------------------------------------------------------------------
# Manejo uniforme de errores no capturados
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _unhandled_exception(_request, exc: Exception):
    logger.exception("Excepcion no manejada: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Error interno del servicio"},
    )
