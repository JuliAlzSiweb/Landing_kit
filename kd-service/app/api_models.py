"""
Modelos Pydantic para la API HTTP del servicio.

El shape EXTERNO (lo que ve el Node) es deliberadamente distinto del shape
INTERNO de `elegibilidad.ResultadoElegibilidad`:

  - Externo: ingles + plano (eligible/message/details). Lo consume Node y
    lo expone tal cual a la landing tras pasarlo por su capa zod.
  - Interno: espanol y rico (elegible/motivo/categoria_preferida/...).

El mapeo lo hace `to_response()` aqui para no acoplar el Node a los nombres
internos del PoC.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .elegibilidad import ImportePorCategoria, ResultadoElegibilidad


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ElegibilidadRequest(BaseModel):
    nif: str = Field(min_length=8, max_length=10, description="NIF/NIE/CIF del beneficiario")
    bono: str = Field(min_length=1, max_length=64, description="Codigo de bono")
    categoria: str = Field(pattern=r"^\d{2}$", description="Categoria preferida (2 digitos)")


# ---------------------------------------------------------------------------
# Response (forma "publica" hacia el Node)
# ---------------------------------------------------------------------------

class AlternativaPublic(BaseModel):
    categoria_id: str
    descripcion: str
    importe_max_segmento: float
    importe_disponible: float
    slot_libre: bool
    acuerdo_existente: str = ""


class DetailsPublic(BaseModel):
    nif: str
    bono: str
    razon_social: str = ""
    segmento: int = 0
    saldo_bono: float = 0.0
    fecha_max_validez_bono: str = ""
    id_convocatoria: str = ""
    categoria_preferida: str = ""
    categoria_preferida_descripcion: str = ""
    importe_categoria_preferida: float = 0.0
    alternativas: list[AlternativaPublic] = Field(default_factory=list)
    duracion_ms: int = 0
    timestamp: str = ""


class ElegibilidadResponse(BaseModel):
    eligible: bool
    message: str
    details: DetailsPublic


def _map_alternativa(alt: ImportePorCategoria) -> AlternativaPublic:
    return AlternativaPublic(
        categoria_id=alt.categoria_id,
        descripcion=alt.descripcion,
        importe_max_segmento=alt.importe_max_segmento,
        importe_disponible=alt.importe_disponible,
        slot_libre=alt.slot_libre,
        acuerdo_existente=alt.acuerdo_existente,
    )


def to_response(r: ResultadoElegibilidad) -> ElegibilidadResponse:
    """Convierte el dataclass interno al shape publico que ve el Node."""
    return ElegibilidadResponse(
        eligible=r.elegible,
        message=r.motivo,
        details=DetailsPublic(
            nif=r.nif,
            bono=r.bono,
            razon_social=r.razon_social,
            segmento=r.segmento,
            saldo_bono=r.saldo_bono,
            fecha_max_validez_bono=r.fecha_max_validez_bono,
            id_convocatoria=r.id_convocatoria,
            categoria_preferida=r.categoria_preferida,
            categoria_preferida_descripcion=r.categoria_preferida_descripcion,
            importe_categoria_preferida=r.importe_categoria_preferida,
            alternativas=[_map_alternativa(a) for a in r.alternativas],
            duracion_ms=r.duracion_ms,
            timestamp=r.timestamp,
        ),
    )


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = None
