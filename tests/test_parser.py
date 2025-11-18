from datetime import datetime
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app import parsear_mensaje, parsear_productos, procesar_fecha, ValidacionError


def test_parsear_mensaje_basico():
    mensaje = """CLIENTE Juan Pérez\nESTADO En tránsito\nFECHA 10/09/2024\n2 calcetas deportivas a 25\n1 pantalon nike a 200\n"""
    cliente, estado, fecha, productos = parsear_mensaje(mensaje)

    assert cliente == "Juan Pérez"
    assert estado == "En tránsito"
    assert fecha == "10/09/2024"
    assert productos == [
        [2, "calcetas deportivas", 25.0, 50.0],
        [1, "pantalon nike", 200.0, 200.0],
    ]


def test_parsear_mensaje_cantidades_en_palabras():
    mensaje = """CLIENTE Ana\nESTADO Pagado\nFECHA 12/01/2025\ntres gorras urbanas x Q45 c/u\n"""
    cliente, estado, fecha, productos = parsear_mensaje(mensaje)

    assert cliente == "Ana"
    assert estado == "Pagado"
    assert fecha == "12/01/2025"
    assert productos == [[3, "gorras urbanas", 45.0, 135.0]]


def test_parsear_mensaje_linea_invalida_reporta_error():
    mensaje = """CLIENTE Test\nESTADO Pendiente\nFECHA 01/02/2024\n2 tenis a 150\n3 producto sin precio\n"""
    with pytest.raises(ValidacionError) as exc:
        parsear_mensaje(mensaje)

    assert "Línea" in str(exc.value)


def test_procesar_fecha_hoy_y_formato():
    hoy = procesar_fecha("HOY")
    assert datetime.strptime(hoy, "%d/%m/%Y")
    assert procesar_fecha("01/03/2024") == "01/03/2024"


def test_procesar_fecha_iso():
    assert procesar_fecha("2024-03-01") == "01/03/2024"


def test_procesar_fecha_invalida():
    with pytest.raises(ValidacionError):
        procesar_fecha("2024/03/01")


def test_parsear_solo_productos():
    texto = """2 calcetas deportivas a 25\n1 pantalon nike a 200"""
    productos = parsear_productos(texto)

    assert productos == [
        [2, "calcetas deportivas", 25.0, 50.0],
        [1, "pantalon nike", 200.0, 200.0],
    ]
