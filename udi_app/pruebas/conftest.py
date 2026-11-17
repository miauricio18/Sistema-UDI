"""Piezas compartidas por todas las pruebas.

Cada prueba recibe un sistema nuevo, en memoria, con los datos de ejemplo y un
reloj fijo en lunes 16 de noviembre de 2026 a las 8:00 (la primera clase empezó 7:55).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from udi.aplicacion import Servicios, iniciar  # noqa: E402
from udi.configuracion import Configuracion, Reloj  # noqa: E402

BOLETA_3CM1 = "2026010001"       # alumno del grupo de la clase actual
OTRA_BOLETA_3CM1 = "2026010002"
BOLETA_3CM2 = "2026020001"       # alumno de otro grupo que sí tiene clase hoy


class RelojFijo(Reloj):
    """Reloj que solo avanza cuando la prueba lo pide."""

    def __init__(self, momento: datetime) -> None:
        self._momento = momento

    def ahora(self) -> datetime:
        return self._momento

    def avanzar(self, minutos: float) -> None:
        self._momento += timedelta(minutes=minutos)


def configuracion_de_prueba(**cambios) -> Configuracion:
    return replace(Configuracion.para_memoria(), **cambios)


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(datetime(2026, 11, 16, 8, 0, 0))


@pytest.fixture
def servicios(reloj):
    sistema = iniciar(configuracion_de_prueba(), datos_ejemplo=True, reloj=reloj)
    yield sistema
    sistema.cerrar()


@pytest.fixture
def clase(servicios: Servicios):
    """La clase en curso (3CM1 en L1)."""
    return servicios.asistencia.obtener_sesion_actual()


@pytest.fixture
def en_disco(tmp_path, reloj):
    """Sistema con base en un archivo real, para probar respaldos y logs."""
    configuracion = Configuracion(carpeta_datos=tmp_path / "UDI")
    sistema = iniciar(configuracion, datos_ejemplo=True, reloj=reloj)
    yield sistema
    sistema.cerrar()
    for salida in list(sistema.logger.handlers):  # suelta udi.log (necesario en Windows)
        sistema.logger.removeHandler(salida)
        salida.close()
