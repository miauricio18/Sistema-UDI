"""Franja de avisos al pie de la ventana: confirma lo que se hizo o explica qué falló."""

from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple

from ..tema import Color, Medida, fuente

_COLORES = {
    "exito": (Color.EXITO_SUAVE, Color.EXITO, "✓"),
    "error": (Color.ERROR_SUAVE, Color.ERROR, "!"),
    "info": (Color.INACTIVO, Color.TEXTO, "i"),
}
_MILISEGUNDOS = {"exito": 4000, "info": 5000, "error": 8000}


class BarraAvisos(tk.Frame):
    """Muestra un mensaje a la vez y lo retira sola. No interrumpe el trabajo."""

    def __init__(self, padre: tk.Misc) -> None:
        super().__init__(padre, background=Color.FONDO, height=1)
        self._etiqueta = tk.Label(
            self, anchor="w", font=fuente(11), padx=Medida.MARGEN, pady=12,
            justify="left",
        )
        self._pendiente: Optional[str] = None
        self.ultimo: Optional[Tuple[str, str]] = None  # (tipo, mensaje); lo usan las pruebas
        self._etiqueta.bind("<Button-1>", lambda _evento: self.ocultar())

    def exito(self, mensaje: str) -> None:
        self._mostrar("exito", mensaje)

    def error(self, mensaje: str) -> None:
        self._mostrar("error", mensaje)

    def info(self, mensaje: str) -> None:
        self._mostrar("info", mensaje)

    def ocultar(self) -> None:
        self._cancelar_temporizador()
        self._etiqueta.pack_forget()

    def _mostrar(self, tipo: str, mensaje: str) -> None:
        fondo, texto, simbolo = _COLORES[tipo]
        self.ultimo = (tipo, mensaje)
        self._cancelar_temporizador()
        self._etiqueta.configure(text=f"{simbolo}   {mensaje}", background=fondo, foreground=texto)
        self._etiqueta.pack(fill="x")
        self._pendiente = self.after(_MILISEGUNDOS[tipo], self.ocultar)

    def _cancelar_temporizador(self) -> None:
        if self._pendiente is not None:
            self.after_cancel(self._pendiente)
            self._pendiente = None
