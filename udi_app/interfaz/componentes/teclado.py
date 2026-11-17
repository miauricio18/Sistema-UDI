"""Teclado numérico en pantalla, para capturar boletas con el dedo."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..tema import Estilo

_TECLAS = (("1", "2", "3"), ("4", "5", "6"), ("7", "8", "9"), ("Borrar", "0", "⌫"))


class TecladoNumerico(ttk.Frame):
    """Escribe sobre una variable de texto; no sabe para qué se usa el número."""

    def __init__(self, padre: tk.Misc, destino: tk.StringVar, largo_maximo: int = 12) -> None:
        super().__init__(padre)
        self._destino = destino
        self._largo_maximo = largo_maximo
        for fila, teclas in enumerate(_TECLAS):
            for columna, tecla in enumerate(teclas):
                boton = ttk.Button(
                    self, text=tecla, style=Estilo.TECLA, takefocus=False, width=-4,
                    command=lambda t=tecla: self.pulsar(t),
                )
                boton.grid(row=fila, column=columna, sticky="nsew", padx=2, pady=2)
        for columna in range(3):
            self.columnconfigure(columna, weight=1, uniform="tecla")

    def pulsar(self, tecla: str) -> None:
        actual = self._destino.get()
        if tecla == "Borrar":
            self._destino.set("")
        elif tecla == "⌫":
            self._destino.set(actual[:-1])
        elif len(actual) < self._largo_maximo:
            self._destino.set(actual + tecla)
