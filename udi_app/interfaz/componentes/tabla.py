"""Tabla con encabezados y barra de desplazamiento."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, NamedTuple, Optional, Sequence

from ..tema import Color


class Columna(NamedTuple):
    clave: str
    titulo: str
    ancho: int
    estira: bool = False
    alineacion: str = "w"


class Fila(NamedTuple):
    identificador: str
    valores: Sequence[object]
    etiqueta: str = ""  # nombre de un color definido con ``colorear``


class Tabla(ttk.Frame):
    """Envuelve un Treeview para que las pantallas solo hablen de filas y columnas."""

    def __init__(
        self,
        padre: tk.Misc,
        columnas: Sequence[Columna],
        al_seleccionar: Optional[Callable[[Optional[str]], None]] = None,
        filas_visibles: int = 8,
    ) -> None:
        super().__init__(padre)
        self._al_seleccionar = al_seleccionar
        self._conocida: Optional[str] = None   # última selección de la que ya se avisó
        self._arbol = ttk.Treeview(
            self, columns=[c.clave for c in columnas], show="headings",
            selectmode="browse", height=filas_visibles,
        )
        for columna in columnas:
            self._arbol.heading(columna.clave, text=columna.titulo, anchor=columna.alineacion)
            self._arbol.column(
                columna.clave, width=columna.ancho, minwidth=40,
                stretch=columna.estira, anchor=columna.alineacion,
            )
        barra = ttk.Scrollbar(self, orient="vertical", command=self._arbol.yview)
        self._arbol.configure(yscrollcommand=barra.set)
        self._arbol.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._arbol.bind("<<TreeviewSelect>>", self._avisar)

    def colorear(self, etiqueta: str, texto: str = Color.TEXTO, fondo: str = Color.FONDO) -> None:
        self._arbol.tag_configure(etiqueta, foreground=texto, background=fondo)

    def cargar(self, filas: Iterable[Fila], seleccion: Optional[str] = None) -> None:
        """Reemplaza el contenido y deja marcada la fila ``seleccion`` si existe.

        Marcar una fila desde aquí no avisa a ``al_seleccionar``: solo se avisa
        cuando la persona toca una fila distinta.
        """
        self._arbol.delete(*self._arbol.get_children())
        for fila in filas:
            self._arbol.insert(
                "", "end", iid=fila.identificador, values=list(fila.valores),
                tags=(fila.etiqueta,) if fila.etiqueta else (),
            )
        self._conocida = None
        if seleccion is not None and self._arbol.exists(seleccion):
            self._conocida = seleccion
            self._arbol.selection_set(seleccion)
            self._arbol.see(seleccion)

    def seleccion(self) -> Optional[str]:
        elegidas = self._arbol.selection()
        return elegidas[0] if elegidas else None

    def identificadores(self) -> Sequence[str]:
        return self._arbol.get_children()

    def _avisar(self, _evento: tk.Event) -> None:
        actual = self.seleccion()
        if actual == self._conocida:
            return
        self._conocida = actual
        if self._al_seleccionar is not None:
            self._al_seleccionar(actual)
