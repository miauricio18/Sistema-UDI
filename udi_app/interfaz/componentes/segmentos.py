"""Grupo de botones donde solo uno queda marcado (por ejemplo: Vino / No vino / Avisó)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Generic, Optional, Sequence, Tuple, TypeVar

from ..tema import Estilo

V = TypeVar("V")


class Segmentos(ttk.Frame, Generic[V]):
    def __init__(
        self,
        padre: tk.Misc,
        opciones: Sequence[Tuple[V, str]],
        al_elegir: Callable[[V], None],
    ) -> None:
        super().__init__(padre)
        self._al_elegir = al_elegir
        self._botones: Dict[V, ttk.Button] = {}
        self._valor: Optional[V] = None
        for columna, (valor, texto) in enumerate(opciones):
            boton = ttk.Button(
                self, text=texto, style=Estilo.SEGMENTO, takefocus=False, width=len(texto) + 1,
                command=lambda v=valor: self._al_elegir(v),
            )
            boton.grid(row=0, column=columna, padx=(0, 4))
            self._botones[valor] = boton

    @property
    def valor(self) -> Optional[V]:
        return self._valor

    def marcar(self, valor: Optional[V]) -> None:
        """Cambia cuál se ve marcado, sin avisar a nadie."""
        self._valor = valor
        for opcion, boton in self._botones.items():
            boton.configure(
                style=Estilo.SEGMENTO_ACTIVO if opcion == valor else Estilo.SEGMENTO
            )
