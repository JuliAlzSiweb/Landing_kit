"""
Tests offline — sin red, usando las respuestas reales capturadas del portal.

Verifica:
  1. El parser DWR (_parse_dwr_response) sobre los 6 responses reales
  2. La lógica de elegibilidad sobre 3 escenarios sintéticos
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Permitir importar el modulo `app` aunque pytest se ejecute desde la raiz
# del repo o desde kd-service/. Insertamos el padre de tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.elegibilidad import (
    _parse_dwr_response,
    _build_importes_lookup,
    _build_descripciones_lookup,
    SessionExpiredError,
    DWRSession,
    comprobar_elegibilidad,
)


# ---------------------------------------------------------------------------
# Respuestas reales capturadas del portal (sustraídas de los .txt del usuario)
# ---------------------------------------------------------------------------

RESPONSE_HAY_ACUERDO_TRUE = '''throw 'allowScriptTagRemoting is false.';
//#DWR-INSERT
//#DWR-REPLY
dwr.engine.remote.handleCallback("10","0","{\\"result\\":\\"true\\", \\"info\\":\\"KD/0001678280\\"}");
'''

RESPONSE_HAY_ACUERDO_FALSE = '''throw 'allowScriptTagRemoting is false.';
//#DWR-INSERT
dwr.engine.remote.handleNewScriptSession("E8B2D912D90C5235B9659E54ED13416F");
//#DWR-REPLY
dwr.engine.remote.handleCallback("10","0","{\\"result\\":\\"false\\", \\"info\\":\\"\\"}");
'''

RESPONSE_DATOS_BENEFICIARIO = '''throw 'allowScriptTagRemoting is false.';
//#DWR-INSERT
//#DWR-REPLY
dwr.engine.remote.handleCallback("5","0","[{\\"idConvocatoria\\":\\"C022/22-SI\\",\\"idExpediente\\":\\"2025/C022/04629936\\",\\"razonSocial\\":\\"SEVIATICO S.L.\\",\\"segmento\\":3,\\"fechaResolucionBono\\":1767049200000,\\"fechaMaxValidezBono\\":1782856799000,\\"renuncia\\":0,\\"saldo\\":3000.0,\\"tieneSaldo\\":true}]");
'''

RESPONSE_CATEGORIAS_BONO = '''throw 'allowScriptTagRemoting is false.';
//#DWR-INSERT
//#DWR-REPLY
dwr.engine.remote.handleCallback("8","0","[{\\"idCategoria\\":\\"01\\"},{\\"idCategoria\\":\\"02\\"},{\\"idCategoria\\":\\"03\\"},{\\"idCategoria\\":\\"04\\"},{\\"idCategoria\\":\\"05\\"},{\\"idCategoria\\":\\"06\\"},{\\"idCategoria\\":\\"07\\"},{\\"idCategoria\\":\\"08\\"},{\\"idCategoria\\":\\"09\\"},{\\"idCategoria\\":\\"10\\"},{\\"idCategoria\\":\\"11\\"},{\\"idCategoria\\":\\"12\\"},{\\"idCategoria\\":\\"14\\"}]");
'''

RESPONSE_DATOS_CATEGORIAS_CONVOCATORIA = '''throw 'allowScriptTagRemoting is false.';
//#DWR-INSERT
//#DWR-REPLY
dwr.engine.remote.handleCallback("6","0","{\\"categorias\\":[{\\"id\\":\\"01\\",\\"descripcion\\":\\"Sitio Web y Presencia B\\u00E1sica en Internet\\"},{\\"id\\":\\"02\\",\\"descripcion\\":\\"Comercio Electr\\u00F3nico\\"},{\\"id\\":\\"03\\",\\"descripcion\\":\\"Gesti\\u00F3n de Redes Sociales\\"},{\\"id\\":\\"04\\",\\"descripcion\\":\\"Gesti\\u00F3n de Clientes\\"},{\\"id\\":\\"05\\",\\"descripcion\\":\\"Business Intelligence y Anal\\u00EDtica\\"},{\\"id\\":\\"06\\",\\"descripcion\\":\\"Gesti\\u00F3n de Procesos\\"},{\\"id\\":\\"07\\",\\"descripcion\\":\\"Factura Electr\\u00F3nica\\"},{\\"id\\":\\"08\\",\\"descripcion\\":\\"Servicios y herramientas de Oficina Virtual\\"},{\\"id\\":\\"09\\",\\"descripcion\\":\\"Comunicaciones Seguras\\"},{\\"id\\":\\"10\\",\\"descripcion\\":\\"Ciberseguridad\\"},{\\"id\\":\\"11\\",\\"descripcion\\":\\"Presencia avanzada en Internet\\"},{\\"id\\":\\"12\\",\\"descripcion\\":\\"Marketplace\\"},{\\"id\\":\\"14\\",\\"descripcion\\":\\"Puesto de trabajo seguro\\"}],\\"categoriasPorImporteTotal\\":[\\"01\\",\\"02\\",\\"03\\",\\"04\\",\\"05\\",\\"06\\",\\"07\\",\\"11\\",\\"12\\",\\"14\\"],\\"maxFinanciablePorCategoria\\":[{\\"categoria\\":\\"01\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":2000.0},{\\"segmento\\":2,\\"importe\\":2000.0},{\\"segmento\\":3,\\"importe\\":2000.0}]},{\\"categoria\\":\\"02\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":2000.0},{\\"segmento\\":2,\\"importe\\":2000.0},{\\"segmento\\":3,\\"importe\\":2000.0}]},{\\"categoria\\":\\"03\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":2500.0},{\\"segmento\\":2,\\"importe\\":2500.0},{\\"segmento\\":3,\\"importe\\":2000.0}]},{\\"categoria\\":\\"04\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":4000.0},{\\"segmento\\":2,\\"importe\\":2000.0},{\\"segmento\\":3,\\"importe\\":2000.0}]},{\\"categoria\\":\\"05\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":4000.0},{\\"segmento\\":2,\\"importe\\":2000.0},{\\"segmento\\":3,\\"importe\\":1500.0}]},{\\"categoria\\":\\"06\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":6000.0},{\\"segmento\\":2,\\"importe\\":3000.0},{\\"segmento\\":3,\\"importe\\":2000.0}]},{\\"categoria\\":\\"07\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":1000.0},{\\"segmento\\":2,\\"importe\\":2000.0},{\\"segmento\\":3,\\"importe\\":1000.0}]},{\\"categoria\\":\\"08\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":250.0},{\\"segmento\\":2,\\"importe\\":250.0},{\\"segmento\\":3,\\"importe\\":250.0}]},{\\"categoria\\":\\"09\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":125.0},{\\"segmento\\":2,\\"importe\\":125.0},{\\"segmento\\":3,\\"importe\\":125.0}]},{\\"categoria\\":\\"10\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":125.0},{\\"segmento\\":2,\\"importe\\":125.0},{\\"segmento\\":3,\\"importe\\":125.0}]},{\\"categoria\\":\\"11\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":0.0},{\\"segmento\\":2,\\"importe\\":2000.0},{\\"segmento\\":3,\\"importe\\":2000.0}]},{\\"categoria\\":\\"12\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":0.0},{\\"segmento\\":2,\\"importe\\":2000.0},{\\"segmento\\":3,\\"importe\\":2000.0}]},{\\"categoria\\":\\"14\\",\\"importes\\":[{\\"segmento\\":1,\\"importe\\":0.0},{\\"segmento\\":2,\\"importe\\":0.0},{\\"segmento\\":3,\\"importe\\":1000.0}]}]}");
'''

RESPONSE_SESION_PERDIDA = '''<html><head><title>Error</title></head>
<body>
<div id="login-container" class="container">
<div class="justify-content-center text-center mb-4">
<h6 class="display-6">Atenci&oacute;n</h6>
<p class="lead">Se ha perdido la sesi&oacute;n. Vuelva...</p>
</div>
</body>
</html>
'''


def test_parser_hay_acuerdo_true():
    result = _parse_dwr_response(RESPONSE_HAY_ACUERDO_TRUE)
    assert result == {"result": "true", "info": "KD/0001678280"}, result
    print("✓ Parser hay_acuerdo TRUE")


def test_parser_hay_acuerdo_false():
    result = _parse_dwr_response(RESPONSE_HAY_ACUERDO_FALSE)
    assert result == {"result": "false", "info": ""}, result
    print("✓ Parser hay_acuerdo FALSE")


def test_parser_datos_beneficiario():
    result = _parse_dwr_response(RESPONSE_DATOS_BENEFICIARIO)
    assert isinstance(result, list)
    assert len(result) == 1
    b = result[0]
    assert b["razonSocial"] == "SEVIATICO S.L.", b
    assert b["segmento"] == 3, b
    assert b["saldo"] == 3000.0, b
    assert b["tieneSaldo"] is True, b
    assert b["idConvocatoria"] == "C022/22-SI", b
    print("✓ Parser datos_beneficiario")


def test_parser_categorias_bono():
    result = _parse_dwr_response(RESPONSE_CATEGORIAS_BONO)
    ids = [item["idCategoria"] for item in result]
    assert ids == ["01","02","03","04","05","06","07","08","09","10","11","12","14"], ids
    print("✓ Parser categorias_bono")


def test_parser_datos_categorias_convocatoria():
    result = _parse_dwr_response(RESPONSE_DATOS_CATEGORIAS_CONVOCATORIA)
    assert "categorias" in result
    assert "maxFinanciablePorCategoria" in result
    cat04 = next(c for c in result["categorias"] if c["id"] == "04")
    assert cat04["descripcion"] == "Gestión de Clientes", cat04
    # Importe categoría 04, segmento 3 = 2000
    importes = _build_importes_lookup(result)
    assert importes[("04", 3)] == 2000.0
    assert importes[("06", 1)] == 6000.0
    assert importes[("01", 3)] == 2000.0
    print("✓ Parser datos_categorias_convocatoria + lookup importes")


def test_parser_sesion_perdida():
    try:
        _parse_dwr_response(RESPONSE_SESION_PERDIDA)
    except SessionExpiredError:
        print("✓ Parser detecta sesión perdida")
        return
    raise AssertionError("Debería haber lanzado SessionExpiredError")


# ---------------------------------------------------------------------------
# Tests del algoritmo de elegibilidad usando mocks de las llamadas DWR
# ---------------------------------------------------------------------------

def _mock_session() -> DWRSession:
    return DWRSession(
        ingress_cookie="x",
        jsessionid="x",
        owasp_csrf="x",
        script_session_id="x",
        window_name="DWR-x",
    )


# Datos sintéticos basados en el caso real
BENEFICIARIO_OK = {
    "idConvocatoria": "C022/22-SI",
    "idExpediente": "2025/C022/04629936",
    "razonSocial": "SEVIATICO S.L.",
    "segmento": 3,
    "fechaResolucionBono": 1767049200000,
    "fechaMaxValidezBono": 1782856799000,  # ~junio 2026
    "renuncia": 0,
    "saldo": 3000.0,
    "tieneSaldo": True,
}

# Catálogo real
import json as _json
CATALOGO = _parse_dwr_response(RESPONSE_DATOS_CATEGORIAS_CONVOCATORIA)

# Categorías aplicables al bono
CATS_BONO = ["01","02","03","04","05","06","07","08","09","10","11","12","14"]


def test_escenario_categoria_libre():
    """Cliente con saldo 3000€, categoría preferida 04 libre — elegible."""
    session = _mock_session()

    with patch("app.elegibilidad.get_datos_beneficiario", return_value=BENEFICIARIO_OK), \
         patch("app.elegibilidad.get_categorias_bono", return_value=CATS_BONO), \
         patch("app.elegibilidad.hay_acuerdo_bono_categoria", return_value=(False, "")):
        r = comprobar_elegibilidad(
            session, "B55467617", "2025/C022/04629936", "04",
            catalogo_cache=CATALOGO,
        )

    assert r.elegible is True, r.motivo
    assert r.razon_social == "SEVIATICO S.L."
    assert r.saldo_bono == 3000.0
    assert r.segmento == 3
    # Categoría 04, segmento 3 → 2000 €. Saldo 3000 € → min(3000, 2000) = 2000
    assert r.importe_categoria_preferida == 2000.0, r.importe_categoria_preferida
    print(f"✓ Escenario categoría libre: elegible, importe {r.importe_categoria_preferida}€")


def test_escenario_categoria_ocupada_con_alternativas():
    """
    Cliente con saldo 3000€, categoría preferida 01 (Sitio Web) ya tiene
    acuerdo KD/0001678280 — NO elegible para 01, pero hay alternativas.
    """
    session = _mock_session()

    def hay_acuerdo_mock(sess, bono, cat):
        # Solo 01 está ocupada, el resto libres
        if cat == "01":
            return (True, "KD/0001678280")
        return (False, "")

    with patch("app.elegibilidad.get_datos_beneficiario", return_value=BENEFICIARIO_OK), \
         patch("app.elegibilidad.get_categorias_bono", return_value=CATS_BONO), \
         patch("app.elegibilidad.hay_acuerdo_bono_categoria", side_effect=hay_acuerdo_mock):
        r = comprobar_elegibilidad(
            session, "B55467617", "2025/C022/04629936", "01",
            catalogo_cache=CATALOGO,
        )

    assert r.elegible is False, "01 ocupada, no debería ser elegible"
    assert "KD/0001678280" in r.motivo, r.motivo
    # Debe haber alternativas, todas libres y con importe > 0
    libres = [a for a in r.alternativas if a.slot_libre and a.importe_disponible > 0]
    assert len(libres) > 5, f"Solo {len(libres)} alternativas libres"
    # La primera alternativa debería tener el importe más alto disponible
    # Cat 06 segmento 3 = 2000, Cat 04 segmento 3 = 2000, etc.
    # Pero todas se topan con saldo 3000, así que múltiples están en 2000
    assert libres[0].importe_disponible >= 2000.0
    print(f"✓ Escenario categoría ocupada: motivo={r.motivo!r}, "
          f"{len(libres)} alternativas elegibles, top={libres[0].categoria_id} "
          f"({libres[0].importe_disponible}€)")


def test_escenario_bono_sin_saldo():
    """Bono existente pero sin saldo — no elegible y sin alternativas."""
    session = _mock_session()
    beneficiario_sin_saldo = {**BENEFICIARIO_OK, "saldo": 0.0, "tieneSaldo": False}

    with patch("app.elegibilidad.get_datos_beneficiario", return_value=beneficiario_sin_saldo):
        r = comprobar_elegibilidad(
            session, "B55467617", "2025/C022/04629936", "04",
            catalogo_cache=CATALOGO,
        )

    assert r.elegible is False
    assert "saldo" in r.motivo.lower()
    assert r.alternativas == []
    print(f"✓ Escenario bono sin saldo: {r.motivo}")


def test_escenario_bono_inexistente():
    """Bono inexistente o no asociado — no elegible."""
    session = _mock_session()

    with patch("app.elegibilidad.get_datos_beneficiario", return_value=None):
        r = comprobar_elegibilidad(
            session, "B99999999", "2025/C022/00000000", "04",
            catalogo_cache=CATALOGO,
        )

    assert r.elegible is False
    assert "no encontrado" in r.motivo.lower() or "no asociado" in r.motivo.lower()
    print(f"✓ Escenario bono inexistente: {r.motivo}")


def test_escenario_categoria_no_aplicable_al_bono():
    """
    Categoría preferida que no está en la lista de cats del bono (ej. 13,
    que es 'Servicio de ciberseguridad gestionada' del catálogo pero no
    aplica a este bono concreto).
    """
    session = _mock_session()

    def hay_acuerdo_mock(sess, bono, cat):
        return (False, "")

    with patch("app.elegibilidad.get_datos_beneficiario", return_value=BENEFICIARIO_OK), \
         patch("app.elegibilidad.get_categorias_bono", return_value=CATS_BONO), \
         patch("app.elegibilidad.hay_acuerdo_bono_categoria", side_effect=hay_acuerdo_mock):
        r = comprobar_elegibilidad(
            session, "B55467617", "2025/C022/04629936", "13",
            catalogo_cache=CATALOGO,
        )

    assert r.elegible is False
    assert "no aplica" in r.motivo.lower()
    # Pero debería haber alternativas válidas
    libres = [a for a in r.alternativas if a.slot_libre and a.importe_disponible > 0]
    assert len(libres) > 5
    print(f"✓ Escenario categoría no aplicable al bono: {len(libres)} alternativas")


if __name__ == "__main__":
    print("=== Tests del parser DWR ===")
    test_parser_hay_acuerdo_true()
    test_parser_hay_acuerdo_false()
    test_parser_datos_beneficiario()
    test_parser_categorias_bono()
    test_parser_datos_categorias_convocatoria()
    test_parser_sesion_perdida()

    print()
    print("=== Tests del algoritmo de elegibilidad ===")
    test_escenario_categoria_libre()
    test_escenario_categoria_ocupada_con_alternativas()
    test_escenario_bono_sin_saldo()
    test_escenario_bono_inexistente()
    test_escenario_categoria_no_aplicable_al_bono()

    print()
    print("Todos los tests pasan ✓")
