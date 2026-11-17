from datetime import date, datetime, time

import pytest

from interfaz import textos
from udi.excepciones import DatosInvalidos


def prueba_fechas_en_espanol_sin_depender_de_windows():
    assert textos.fecha_larga(date(2026, 11, 16)) == "Lunes 16 de noviembre de 2026"
    assert textos.fecha_corta(date(2026, 3, 5)) == "05/03/2026"
    assert textos.nombre_mes(date(2026, 1, 31)) == "Enero 2026"
    assert textos.hora(datetime(2026, 11, 16, 7, 5)) == "07:05"
    assert textos.hora(None) == ""
    assert textos.fecha_hora(None) == "—"


@pytest.mark.parametrize("texto", ["16/11/2026", "16-11-2026", "2026-11-16", " 16/11/2026 "])
def prueba_leer_fecha(texto):
    assert textos.leer_fecha(texto) == date(2026, 11, 16)


@pytest.mark.parametrize("texto, esperada", [("07:00", time(7)), ("13.30", time(13, 30)), ("0705", time(7, 5))])
def prueba_leer_hora(texto, esperada):
    assert textos.leer_hora(texto) == esperada


@pytest.mark.parametrize("lector, texto", [
    (textos.leer_fecha, "mañana"), (textos.leer_fecha, "31/02/2026"), (textos.leer_fecha, ""),
    (textos.leer_hora, "25:00"), (textos.leer_hora, "siete"), (textos.leer_hora, None),
])
def prueba_lo_mal_escrito_avisa_con_un_mensaje_claro(lector, texto):
    with pytest.raises(DatosInvalidos):
        lector(texto)


def prueba_leer_entero():
    assert textos.leer_entero(" 40 ", "El total") == 40
    with pytest.raises(DatosInvalidos):
        textos.leer_entero("cuarenta", "El total")


def prueba_textos_cortos():
    assert textos.nombre_corto("Sofía García") == "Sofía"
    assert textos.nombre_corto("Maximiliano Cruz") == "Maximil…"
    assert textos.nombre_corto("") == ""
    assert textos.tamano(108 * 1024) == "108 KB"
    assert textos.tamano(3 * 1024 * 1024) == "3.0 MB"
    assert textos.porcentaje(5, 12) == "42 %"
    assert textos.porcentaje(0, 0) == "—"
