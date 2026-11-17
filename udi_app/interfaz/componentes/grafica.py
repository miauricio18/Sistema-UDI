"""Gráfica de barras sencilla, dibujada con el Canvas de Tkinter (sin paquetes extra)."""

from __future__ import annotations

import tkinter as tk
from typing import NamedTuple, Sequence

from ..tema import Color, fuente

_MARGEN_IZQUIERDO = 44
_MARGEN_INFERIOR = 28
_MARGEN_SUPERIOR = 24
_ANCHO_MAXIMO_BARRA = 56
_ANCHO_MINIMO_CON_TEXTO = 34


class Barra(NamedTuple):
    etiqueta: str
    parte: int
    total: int


class GraficaBarras(tk.Canvas):
    """Cada barra muestra qué fracción del total se alcanzó (de 0 a 100 %)."""

    def __init__(self, padre: tk.Misc, alto: int = 220, vacio: str = "Sin datos en este periodo.") -> None:
        super().__init__(padre, height=alto, background=Color.FONDO, highlightthickness=0)
        self._barras: Sequence[Barra] = ()
        self._vacio = vacio
        self.bind("<Configure>", lambda _evento: self._dibujar())

    def cargar(self, barras: Sequence[Barra]) -> None:
        self._barras = barras
        self._dibujar()

    def _dibujar(self) -> None:
        self.delete("all")
        ancho, alto = self.winfo_width(), self.winfo_height()
        if ancho < 2 * _MARGEN_IZQUIERDO:
            return
        if not self._barras:
            self.create_text(ancho / 2, alto / 2, text=self._vacio,
                             fill=Color.TEXTO_SUAVE, font=fuente(11))
            return

        base = alto - _MARGEN_INFERIOR
        altura_util = base - _MARGEN_SUPERIOR
        for fraccion in (0, 0.5, 1):
            y = base - altura_util * fraccion
            self.create_line(_MARGEN_IZQUIERDO, y, ancho, y, fill=Color.BORDE)
            self.create_text(_MARGEN_IZQUIERDO - 8, y, text=f"{int(fraccion * 100)} %",
                             anchor="e", fill=Color.TEXTO_SUAVE, font=fuente(9))

        paso = (ancho - _MARGEN_IZQUIERDO) / len(self._barras)
        ancho_barra = min(_ANCHO_MAXIMO_BARRA, paso * 0.6)
        con_texto = paso >= _ANCHO_MINIMO_CON_TEXTO
        for indice, barra in enumerate(self._barras):
            centro = _MARGEN_IZQUIERDO + paso * (indice + 0.5)
            fraccion = barra.parte / barra.total if barra.total else 0
            cima = base - altura_util * fraccion
            self.create_rectangle(centro - ancho_barra / 2, cima, centro + ancho_barra / 2, base,
                                  fill=Color.ACENTO, outline="")
            if con_texto:
                self.create_text(centro, cima - 10, text=f"{barra.parte}/{barra.total}",
                                 fill=Color.TEXTO, font=fuente(9))
                self.create_text(centro, base + 14, text=barra.etiqueta,
                                 fill=Color.TEXTO_SUAVE, font=fuente(9))
