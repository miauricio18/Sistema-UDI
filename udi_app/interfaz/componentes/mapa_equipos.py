"""Mapa del laboratorio: un cuadro por computadora, que se toca para asignarla."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from udi.modelos import Equipo, EstadoEquipo

from ..tema import Color, fuente
from ..textos import nombre_corto

# (fondo, texto, borde) de cada estado. El texto del cuadro también dice el
# estado, para no depender solo del color.
_ASPECTO: Dict[EstadoEquipo, Tuple[str, str, str]] = {
    EstadoEquipo.LIBRE: (Color.FONDO, Color.TEXTO, Color.BORDE),
    EstadoEquipo.OCUPADO: (Color.ACENTO_SUAVE, Color.ACENTO, Color.ACENTO_SUAVE),
    EstadoEquipo.FUERA_DE_SERVICIO: (Color.INACTIVO, Color.TEXTO_SUAVE, Color.INACTIVO),
}
_ASPECTO_RESALTADO = (Color.ACENTO, Color.SOBRE_ACENTO, Color.ACENTO)
_COLUMNAS = 10


class MapaEquipos(ttk.Frame):
    """Solo dibuja y avisa qué número se tocó; la decisión es de la pantalla."""

    def __init__(self, padre: tk.Misc, al_tocar: Callable[[int], None]) -> None:
        super().__init__(padre)
        self._al_tocar = al_tocar
        self._cuadros: Dict[int, Tuple[tk.Frame, tk.Button]] = {}
        self._numeros: List[int] = []

    def cargar(self, equipos: Sequence[Equipo], resaltado: Optional[int] = None) -> None:
        numeros = [e.numero for e in equipos]
        if numeros != self._numeros:
            self._reconstruir(numeros)
        for equipo in equipos:
            self._pintar(equipo, equipo.numero == resaltado)

    def _reconstruir(self, numeros: List[int]) -> None:
        for marco, _boton in self._cuadros.values():
            marco.destroy()
        self._cuadros.clear()
        self._numeros = numeros
        columnas = _COLUMNAS
        for posicion, numero in enumerate(numeros):
            marco = tk.Frame(self, background=Color.BORDE)
            boton = tk.Button(
                marco, relief="flat", borderwidth=0, highlightthickness=0, takefocus=False,
                font=fuente(10), height=2, cursor="hand2",
                command=lambda n=numero: self._al_tocar(n),
            )
            boton.pack(fill="both", expand=True, padx=1, pady=1)
            marco.grid(row=posicion // columnas, column=posicion % columnas,
                       sticky="nsew", padx=3, pady=3)
            self._cuadros[numero] = (marco, boton)
        for columna in range(columnas):
            self.columnconfigure(columna, weight=1, uniform="equipo")

    def _pintar(self, equipo: Equipo, resaltado: bool) -> None:
        marco, boton = self._cuadros[equipo.numero]
        fondo, texto, borde = _ASPECTO_RESALTADO if resaltado else _ASPECTO[equipo.estado]
        if equipo.estado is EstadoEquipo.FUERA_DE_SERVICIO:
            detalle = "Fuera"
        elif equipo.alumno_actual is not None:
            detalle = nombre_corto(equipo.alumno_actual.nombre)
        else:
            detalle = "Libre"
        marco.configure(background=borde)
        boton.configure(
            text=f"{equipo.numero}\n{detalle}", background=fondo, foreground=texto,
            activebackground=fondo, activeforeground=texto,
        )
