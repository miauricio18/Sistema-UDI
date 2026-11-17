"""Funciones chicas de texto que usan varios módulos."""

from __future__ import annotations

import unicodedata
from typing import Any


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sin acentos y con espacios simples. Sirve para buscar y comparar."""
    sin_acentos = "".join(
        letra
        for letra in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(letra)
    )
    return " ".join(sin_acentos.lower().split())


def a_texto(valor: Any) -> str:
    """Convierte cualquier celda a texto limpio (None queda como cadena vacía)."""
    if valor is None:
        return ""
    return str(valor).strip()


def a_texto_boleta(valor: Any) -> str:
    """Lee la boleta SIEMPRE como texto: Excel la puede entregar como número."""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return a_texto(valor)
