"""Revisión de los datos que entran al sistema, antes de aplicar cualquier regla.

Cada función devuelve el valor ya limpio o lanza ``DatosInvalidos`` con un
mensaje listo para la pantalla.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Type, TypeVar

from .excepciones import DatosInvalidos
from .utilidades import a_texto, a_texto_boleta

# Supuesto: boleta de 6 a 12 letras o dígitos (la del IPN tiene 10 dígitos).
_PATRON_BOLETA = re.compile(r"^[0-9A-Za-z]{6,12}$")
_PATRON_CLAVE = re.compile(r"^[0-9A-Za-z_-]{1,20}$")
_CARACTERES_DE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

NUMERO_EQUIPO_MAXIMO = 999
LARGO_MAXIMO_NOMBRE = 120

E = TypeVar("E", bound=Enum)


def es_boleta_valida(boleta: Any) -> bool:
    return bool(_PATRON_BOLETA.match(a_texto_boleta(boleta)))


def es_clave_valida(clave: Any) -> bool:
    """Claves cortas sin espacios: grupo (3CM1) o laboratorio (L1)."""
    return bool(_PATRON_CLAVE.match(a_texto(clave)))


def validar_clave(clave: Any, campo: str) -> str:
    texto = a_texto(clave)
    if not _PATRON_CLAVE.match(texto):
        raise DatosInvalidos(f"{campo} no es válido: usa solo letras, números y guiones.")
    return texto


def validar_texto(valor: Any, campo: str, maximo: int, minimo: int = 1) -> str:
    """Quita espacios sobrantes y caracteres invisibles, y revisa el largo."""
    texto = _CARACTERES_DE_CONTROL.sub("", a_texto(valor))
    if len(texto) < minimo:
        raise DatosInvalidos(f"Falta escribir: {campo}.")
    if len(texto) > maximo:
        raise DatosInvalidos(f"{campo} es demasiado largo (máximo {maximo} caracteres).")
    return texto


def validar_numero_equipo(numero: Any) -> int:
    if isinstance(numero, bool) or not isinstance(numero, int):
        raise DatosInvalidos("El número de computadora debe ser un número entero.")
    if not 1 <= numero <= NUMERO_EQUIPO_MAXIMO:
        raise DatosInvalidos("El número de computadora no es válido.")
    return numero


def validar_enum(valor: Any, tipo: Type[E], campo: str) -> E:
    """Acepta el Enum o su texto ("VINO"); cualquier otra cosa es un error."""
    try:
        return tipo(valor)
    except ValueError as error:
        raise DatosInvalidos(f"{campo} no es una opción válida.") from error
