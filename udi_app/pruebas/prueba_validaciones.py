import pytest

from udi.excepciones import DatosInvalidos
from udi.modelos import EstadoMaestro
from udi.utilidades import a_texto_boleta
from udi.validaciones import (
    es_boleta_valida,
    es_clave_valida,
    validar_enum,
    validar_texto,
)


@pytest.mark.parametrize("boleta", ["2026010001", "PE12345678", 2026010001, 2026010001.0])
def prueba_boletas_validas(boleta):
    assert es_boleta_valida(boleta)


@pytest.mark.parametrize("boleta", ["", "123", "2026 010001", "2026-010001", "x" * 13, None, "'; --"])
def prueba_boletas_invalidas(boleta):
    assert not es_boleta_valida(boleta)


def prueba_excel_entrega_la_boleta_como_decimal():
    assert a_texto_boleta(2026010001.0) == "2026010001"


@pytest.mark.parametrize("clave, valida", [("3CM1", True), ("L1", True), ("3 CM1", False), ("", False), ("a;b", False)])
def prueba_claves(clave, valida):
    assert es_clave_valida(clave) is valida


def prueba_texto_se_limpia_y_se_mide():
    assert validar_texto("  hola\x00 \x07mundo  ", "el texto", maximo=20) == "hola mundo"
    with pytest.raises(DatosInvalidos):
        validar_texto("   ", "el texto", maximo=20)
    with pytest.raises(DatosInvalidos):
        validar_texto("x" * 21, "el texto", maximo=20)


def prueba_enum_acepta_el_valor_o_su_texto():
    assert validar_enum("VINO", EstadoMaestro, "El estado") is EstadoMaestro.VINO
    assert validar_enum(EstadoMaestro.AVISO, EstadoMaestro, "El estado") is EstadoMaestro.AVISO
    with pytest.raises(DatosInvalidos):
        validar_enum("QUIZAS", EstadoMaestro, "El estado")
