"""
PoC — Consulta de elegibilidad de bono Kit Digital contra portal adacuerdos.

Responde a la pregunta de negocio:
  Dado (NIF beneficiario, código de bono, categoría preferida),
  ¿puede el cliente firmar un acuerdo con nosotros, y por cuánto?

NO incluye el login con certificado .p12 — eso lo añade el equipo de Siweb
con Playwright en su entorno controlado. Este script asume que recibe
cookies de sesión ya autenticadas (INGRESSCOOKIE + JSESSIONID + csrf token
+ scriptSessionId) y opera contra ellas.

Uso:
    python elegibilidad.py \\
        --nif B55467617 \\
        --bono 2025/C022/04629936 \\
        --categoria 04 \\
        --cookies-file cookies.json

cookies.json debe contener:
    {
        "INGRESSCOOKIE": "...",
        "JSESSIONID": "...",
        "owasp_csrf": "...",
        "script_session_id": "...",
        "window_name": "DWR-..."
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any
from urllib.parse import quote

import requests


BASE_URL = "https://portal.gestion.sedepkd.red.gob.es"
DWR_PATH = "/adacuerdos/dwr/call/plaincall"
REFERER = f"{BASE_URL}/adacuerdos/action/solicitudForm"

# Regex para extraer el JSON de la respuesta DWR.
# Las respuestas tienen la forma:
#   dwr.engine.remote.handleCallback("BATCH","ID","PAYLOAD_ESCAPADO");
# donde PAYLOAD_ESCAPADO es un string con backslashes ante las comillas.
_HANDLE_CALLBACK_RE = re.compile(
    r'dwr\.engine\.remote\.handleCallback\("(\d+)","(\d+)","(.*)"\);',
    re.DOTALL,
)

# Detector de sesión expirada: el portal devuelve HTML con este texto.
_SESION_PERDIDA_MARKERS = (
    "Se ha perdido la sesi",  # acentos pueden venir como entidad HTML
    "login-container",
)


class DWRError(Exception):
    """Error genérico de la capa DWR."""


class SessionExpiredError(DWRError):
    """La sesión ha expirado y hace falta re-loginar."""


@dataclass
class DWRSession:
    """Estado mínimo de una sesión autenticada contra el portal."""

    ingress_cookie: str
    jsessionid: str
    owasp_csrf: str
    script_session_id: str
    window_name: str  # ej. "DWR-F297AC7BB40353EDB65996516C79EB59"
    batch_counter: int = 0  # se incrementa en cada llamada

    @classmethod
    def from_file(cls, path: str) -> "DWRSession":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            ingress_cookie=data["INGRESSCOOKIE"],
            jsessionid=data["JSESSIONID"],
            owasp_csrf=data["owasp_csrf"],
            script_session_id=data["script_session_id"],
            window_name=data["window_name"],
        )

    def next_batch_id(self) -> int:
        self.batch_counter += 1
        return self.batch_counter


def _parse_dwr_response(body: str) -> Any:
    """
    Parsea una respuesta DWR y devuelve el payload deserializado.

    Maneja tres casos:
      1. Respuesta exitosa con JSON: handleCallback(..., "{...}")
      2. Respuesta exitosa con array: handleCallback(..., "[...]")
      3. Sesión expirada: HTML con login-container o "perdido la sesión"
    """
    # Detectar sesión expirada primero
    if any(marker in body for marker in _SESION_PERDIDA_MARKERS):
        raise SessionExpiredError("La sesión ha expirado, hay que re-loginar")

    match = _HANDLE_CALLBACK_RE.search(body)
    if not match:
        raise DWRError(
            f"Respuesta DWR sin handleCallback reconocible. "
            f"Primeros 200 chars: {body[:200]!r}"
        )

    raw_payload = match.group(3)

    # El payload viene con backslashes ante comillas internas.
    # Para deserializarlo, lo metemos como string en JSON y dejamos que
    # json.loads desescape.
    try:
        unescaped = json.loads(f'"{raw_payload}"')
    except json.JSONDecodeError as e:
        raise DWRError(f"No se pudo desescapar payload DWR: {e}") from e

    # Algunas respuestas devuelven JSON estructurado, otras string suelto
    try:
        return json.loads(unescaped)
    except json.JSONDecodeError:
        # No es JSON — devolver el string crudo
        return unescaped


def _dwr_call(
    session: DWRSession,
    script_name: str,
    method_name: str,
    params: list[str | None],
) -> Any:
    """
    Realiza una llamada DWR al portal.

    params: lista de valores (str para strings, None para nulls).
            Internamente se URL-encodifican y se prefijan según el tipo.
    """
    batch_id = session.next_batch_id()

    # Construir el cuerpo de la request DWR
    lines = [
        "callCount=1",
        f"windowName={session.window_name}",
        f"c0-scriptName={script_name}",
        f"c0-methodName={method_name}",
        "c0-id=0",
    ]

    for i, value in enumerate(params):
        if value is None:
            lines.append(f"c0-param{i}=null:null")
        else:
            # URL-encode los caracteres especiales (/, espacios...)
            # como hace el navegador (%2F para /).
            encoded = quote(str(value), safe="")
            lines.append(f"c0-param{i}=string:{encoded}")

    lines.extend([
        f"batchId={batch_id}",
        "page=/adacuerdos/action/solicitudForm",
        "httpSessionId=",
        f"scriptSessionId={session.script_session_id}",
        "",  # newline final
    ])

    body = "\n".join(lines)

    headers = {
        "accept": "*/*",
        "accept-language": "es-ES,es;q=0.9",
        "cache-control": "no-cache",
        "content-type": "text/plain",
        "origin": BASE_URL,
        "owasp-csrftoken": session.owasp_csrf,
        "pragma": "no-cache",
        "referer": REFERER,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
        "x-requested-with": "XMLHttpRequest",
    }

    cookies = {
        "INGRESSCOOKIE": session.ingress_cookie,
        "JSESSIONID": session.jsessionid,
    }

    url = f"{BASE_URL}{DWR_PATH}/{script_name}.{method_name}.dwr"

    try:
        response = requests.post(
            url,
            data=body,
            headers=headers,
            cookies=cookies,
            timeout=30,
        )
    except requests.RequestException as e:
        # Errores de red / timeout / DNS — convertir a DWRError para que el
        # endpoint los exponga limpiamente en vez de un 500 generico.
        raise DWRError(f"Error de red llamando a {script_name}.{method_name}: {e}") from e

    if response.status_code >= 500:
        # 5xx del portal (501, 502, 503...). Suelen ser transitorios del WAF.
        # Lo expone como DWRError; el cliente puede reintentar.
        raise DWRError(
            f"Portal devolvio HTTP {response.status_code} en "
            f"{script_name}.{method_name} — error transitorio del portal de Red.es"
        )
    response.raise_for_status()  # 4xx (raros aqui) tambien -> HTTPError
    return _parse_dwr_response(response.text)


# ---------------------------------------------------------------------------
# Wrappers de alto nivel sobre las 6 llamadas DWR del portal
# ---------------------------------------------------------------------------

def get_datos_beneficiario(
    session: DWRSession, nif: str, bono: str
) -> dict | None:
    """
    Devuelve los datos del beneficiario asociado a un bono, o None si el
    bono no existe / no está asociado a ese NIF.

    Campos relevantes en el dict devuelto:
      - razonSocial: nombre legal de la empresa
      - segmento: 1, 2 o 3 (determina importes máximos)
      - saldo: importe en euros aún disponible (no validado todavía)
      - tieneSaldo: bool
      - fechaMaxValidezBono: epoch ms hasta cuándo es válido el bono
      - idConvocatoria: ej. "C022/22-SI"
    """
    result = _dwr_call(
        session,
        "RemoteMicroService",
        "getDatosBeneficiarioADA",
        [nif, "", bono],
    )
    if not result:
        return None
    # El portal devuelve un array; el primer elemento es el beneficiario.
    return result[0] if isinstance(result, list) else result


def get_datos_categorias_convocatoria(
    session: DWRSession, id_convocatoria: str
) -> dict:
    """
    Devuelve el catálogo completo de la convocatoria:
      - categorias: lista de {id, descripcion}
      - maxFinanciablePorCategoria: lista de {categoria, importes:[{segmento,importe}]}
      - categoriasPorImporteTotal: lista de IDs que aplican por importe total
      - maxUnidadesFinanciableSegmento: para categorías que se miden en unidades
    """
    return _dwr_call(
        session,
        "RemoteMicroService",
        "getDatosCategoriasConvocatoria",
        [id_convocatoria],
    )


def get_categorias_bono(session: DWRSession, bono: str) -> list[str]:
    """
    Devuelve la lista de IDs de categorías aplicables a este bono concreto
    (subconjunto del catálogo de la convocatoria).
    """
    result = _dwr_call(
        session,
        "RemoteMicroService",
        "getCategoriasBono",
        [bono, None],
    )
    return [item["idCategoria"] for item in result]


def hay_acuerdo_bono_categoria(
    session: DWRSession, bono: str, categoria: str
) -> tuple[bool, str]:
    """
    Comprueba si ya existe un acuerdo (firmado, validado o no) para este
    bono y categoría.

    Devuelve (existe, codigo_acuerdo). Si no existe, codigo_acuerdo es "".
    """
    result = _dwr_call(
        session,
        "RemoteAgreementData",
        "hayAcuerdosBonoCategoriaADA",
        ["", bono, categoria, ""],
    )
    existe = str(result.get("result", "")).lower() == "true"
    info = result.get("info", "")
    return existe, info


# ---------------------------------------------------------------------------
# Lógica de negocio: algoritmo de elegibilidad
# ---------------------------------------------------------------------------

@dataclass
class ImportePorCategoria:
    categoria_id: str
    descripcion: str
    importe_max_segmento: float
    importe_disponible: float  # min(saldo_bono, importe_max_segmento)
    slot_libre: bool
    acuerdo_existente: str = ""  # código del acuerdo si slot ocupado


@dataclass
class ResultadoElegibilidad:
    elegible: bool
    motivo: str
    bono: str
    nif: str
    razon_social: str = ""
    segmento: int = 0
    saldo_bono: float = 0.0
    fecha_max_validez_bono: str = ""
    id_convocatoria: str = ""
    categoria_preferida: str = ""
    categoria_preferida_descripcion: str = ""
    importe_categoria_preferida: float = 0.0
    alternativas: list[ImportePorCategoria] = field(default_factory=list)
    duracion_ms: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _build_importes_lookup(catalogo: dict) -> dict[tuple[str, int], float]:
    """
    A partir del payload de getDatosCategoriasConvocatoria, construye un
    diccionario {(categoria_id, segmento): importe_max}.
    """
    lookup: dict[tuple[str, int], float] = {}
    for item in catalogo.get("maxFinanciablePorCategoria", []):
        cat_id = item["categoria"]
        for importe_seg in item.get("importes", []):
            lookup[(cat_id, importe_seg["segmento"])] = importe_seg["importe"]
    return lookup


def _build_descripciones_lookup(catalogo: dict) -> dict[str, str]:
    return {
        cat["id"]: cat["descripcion"]
        for cat in catalogo.get("categorias", [])
    }


def comprobar_elegibilidad(
    session: DWRSession,
    nif: str,
    bono: str,
    categoria_preferida: str,
    catalogo_cache: dict | None = None,
) -> ResultadoElegibilidad:
    """
    Algoritmo principal. Recorre las 6 llamadas DWR siguiendo la lógica
    descrita en la conversación de diseño.

    Si se pasa catalogo_cache (resultado previo de
    getDatosCategoriasConvocatoria), se evita una llamada al portal —
    útil porque el catálogo es estable durante la convocatoria.
    """
    inicio = time.monotonic()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    # PASO 1 — datos del beneficiario y validación inicial del bono
    beneficiario = get_datos_beneficiario(session, nif, bono)
    if beneficiario is None:
        return ResultadoElegibilidad(
            elegible=False,
            motivo="Bono no encontrado o no asociado a este NIF",
            bono=bono,
            nif=nif,
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            timestamp=timestamp,
        )

    if not beneficiario.get("tieneSaldo") or beneficiario.get("saldo", 0) <= 0:
        return ResultadoElegibilidad(
            elegible=False,
            motivo="El bono no tiene saldo disponible",
            bono=bono,
            nif=nif,
            razon_social=beneficiario.get("razonSocial", ""),
            segmento=beneficiario.get("segmento", 0),
            saldo_bono=beneficiario.get("saldo", 0),
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            timestamp=timestamp,
        )

    # Validez del bono — comparar fecha actual con fechaMaxValidezBono
    fecha_max_ms = beneficiario.get("fechaMaxValidezBono", 0)
    ahora_ms = int(time.time() * 1000)
    if fecha_max_ms and fecha_max_ms < ahora_ms:
        return ResultadoElegibilidad(
            elegible=False,
            motivo="El bono está caducado",
            bono=bono,
            nif=nif,
            razon_social=beneficiario.get("razonSocial", ""),
            saldo_bono=beneficiario.get("saldo", 0),
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            timestamp=timestamp,
        )

    saldo = float(beneficiario["saldo"])
    segmento = int(beneficiario["segmento"])
    razon_social = beneficiario.get("razonSocial", "")
    id_convocatoria = beneficiario.get("idConvocatoria", "")
    fecha_max_str = time.strftime(
        "%Y-%m-%d", time.gmtime(fecha_max_ms / 1000)
    ) if fecha_max_ms else ""

    # PASO 2 — catálogo de la convocatoria (cacheable)
    if catalogo_cache is not None:
        catalogo = catalogo_cache
    else:
        catalogo = get_datos_categorias_convocatoria(session, id_convocatoria)

    importes_lookup = _build_importes_lookup(catalogo)
    descripciones = _build_descripciones_lookup(catalogo)

    # PASO 3 — categorías permitidas para este bono
    cats_bono = get_categorias_bono(session, bono)

    # PASO 4 — validar categoría preferida
    if categoria_preferida not in cats_bono:
        # No aplicable, pero seguimos para proponer alternativas
        importe_preferida = 0.0
        slot_preferida_libre = False
        acuerdo_existente_preferida = ""
        motivo_preferida = (
            f"La categoría {categoria_preferida} no aplica a este bono"
        )
    else:
        existe, codigo = hay_acuerdo_bono_categoria(
            session, bono, categoria_preferida
        )
        slot_preferida_libre = not existe
        acuerdo_existente_preferida = codigo
        importe_max_pref = importes_lookup.get(
            (categoria_preferida, segmento), 0.0
        )
        importe_preferida = (
            min(saldo, importe_max_pref) if slot_preferida_libre else 0.0
        )
        motivo_preferida = (
            "Elegible para la categoría preferida"
            if slot_preferida_libre
            else f"Ya existe un acuerdo {codigo} para esta categoría"
        )

    # PASO 5 — alternativas (solo si la preferida no es elegible o queremos
    # ofrecer comparación)
    alternativas: list[ImportePorCategoria] = []
    necesita_alternativas = not slot_preferida_libre or importe_preferida == 0

    if necesita_alternativas:
        for cat_id in cats_bono:
            if cat_id == categoria_preferida:
                continue
            importe_max = importes_lookup.get((cat_id, segmento), 0.0)
            if importe_max <= 0:
                # Categoría sin importe para este segmento — saltar
                continue
            existe, codigo = hay_acuerdo_bono_categoria(session, bono, cat_id)
            slot_libre = not existe
            disponible = min(saldo, importe_max) if slot_libre else 0.0
            alternativas.append(
                ImportePorCategoria(
                    categoria_id=cat_id,
                    descripcion=descripciones.get(cat_id, ""),
                    importe_max_segmento=importe_max,
                    importe_disponible=disponible,
                    slot_libre=slot_libre,
                    acuerdo_existente=codigo,
                )
            )
        # Ordenar alternativas: primero las elegibles, dentro por importe
        alternativas.sort(
            key=lambda a: (not a.slot_libre, -a.importe_disponible)
        )

    elegible = slot_preferida_libre and importe_preferida > 0
    motivo = motivo_preferida

    return ResultadoElegibilidad(
        elegible=elegible,
        motivo=motivo,
        bono=bono,
        nif=nif,
        razon_social=razon_social,
        segmento=segmento,
        saldo_bono=saldo,
        fecha_max_validez_bono=fecha_max_str,
        id_convocatoria=id_convocatoria,
        categoria_preferida=categoria_preferida,
        categoria_preferida_descripcion=descripciones.get(
            categoria_preferida, ""
        ),
        importe_categoria_preferida=importe_preferida,
        alternativas=alternativas,
        duracion_ms=int((time.monotonic() - inicio) * 1000),
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Comprueba elegibilidad de bono Kit Digital"
    )
    parser.add_argument("--nif", required=True, help="NIF del beneficiario")
    parser.add_argument("--bono", required=True, help="Código de bono")
    parser.add_argument(
        "--categoria", required=True, help="Categoría preferida (ej. 04)"
    )
    parser.add_argument(
        "--cookies-file",
        required=True,
        help="Ruta a JSON con cookies y tokens de sesión",
    )
    parser.add_argument(
        "--output",
        choices=["json", "human"],
        default="human",
        help="Formato de salida",
    )
    args = parser.parse_args()

    session = DWRSession.from_file(args.cookies_file)

    try:
        resultado = comprobar_elegibilidad(
            session=session,
            nif=args.nif,
            bono=args.bono,
            categoria_preferida=args.categoria,
        )
    except SessionExpiredError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Re-loginar y reintentar.", file=sys.stderr)
        return 2
    except DWRError as e:
        print(f"ERROR DWR: {e}", file=sys.stderr)
        return 3

    if args.output == "json":
        print(json.dumps(resultado.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print_human(resultado)

    return 0 if resultado.elegible else 1


def _print_human(r: ResultadoElegibilidad) -> None:
    print(f"=== Resultado de elegibilidad ===")
    print(f"Beneficiario:    {r.razon_social} ({r.nif})")
    print(f"Bono:            {r.bono}")
    print(f"Convocatoria:    {r.id_convocatoria}")
    print(f"Segmento:        {r.segmento}")
    print(f"Saldo bono:      {r.saldo_bono:.2f} €")
    print(f"Válido hasta:    {r.fecha_max_validez_bono}")
    print()
    print(
        f"Categoría preferida: {r.categoria_preferida} — "
        f"{r.categoria_preferida_descripcion}"
    )
    print(f"  Elegible:    {'SÍ' if r.elegible else 'NO'}")
    print(f"  Motivo:      {r.motivo}")
    if r.elegible:
        print(f"  Importe:     {r.importe_categoria_preferida:.2f} €")

    if r.alternativas:
        print()
        print("Alternativas:")
        for alt in r.alternativas:
            estado = "libre" if alt.slot_libre else f"ocupado ({alt.acuerdo_existente})"
            print(
                f"  [{alt.categoria_id}] {alt.descripcion[:50]:<50} "
                f"max {alt.importe_max_segmento:>7.2f} € | "
                f"disponible {alt.importe_disponible:>7.2f} € | "
                f"{estado}"
            )

    print()
    print(f"(consulta en {r.duracion_ms} ms — {r.timestamp})")


if __name__ == "__main__":
    sys.exit(main())
