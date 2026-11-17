"""Molde de todas las pantallas.

Para agregar una pantalla: crear una clase que herede de ``Pantalla`` en un
archivo nuevo de esta carpeta y añadirla a ``PANTALLAS`` en ``__init__.py``.
Nada más cambia: el menú y la navegación se arman solos.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import ClassVar

from ..contexto import Contexto
from ..tema import Estilo, Medida


class Pantalla(ttk.Frame):
    """Una sección de la aplicación. Dibuja y llama a los servicios; no decide reglas."""

    clave: ClassVar[str] = ""    # identificador interno, único
    titulo: ClassVar[str] = ""   # texto del menú y del encabezado

    def __init__(self, padre: tk.Misc, contexto: Contexto) -> None:
        super().__init__(padre, padding=Medida.MARGEN)
        self.contexto = contexto
        self.servicios = contexto.servicios
        self.construir()

    # -- lo que cada pantalla define ------------------------------------------
    def construir(self) -> None:
        """Crea los controles. Se llama una sola vez."""
        raise NotImplementedError

    def al_mostrar(self) -> None:
        """Vuelve a leer los datos. Se llama cada vez que la pantalla aparece."""

    def al_pasar_tiempo(self) -> None:
        """Se llama cada medio minuto mientras la pantalla está visible."""

    # -- ayudas comunes --------------------------------------------------------
    def hoy(self) -> date:
        return self.servicios.reloj.ahora().date()

    def encabezado(self, padre: tk.Misc) -> ttk.Frame:
        """Título de la pantalla; devuelve el marco para poner acciones a la derecha."""
        marco = ttk.Frame(padre)
        ttk.Label(marco, text=self.titulo, style=Estilo.TITULO).pack(side="left")
        return marco

    @staticmethod
    def linea(padre: tk.Misc) -> ttk.Frame:
        return ttk.Frame(padre, style=Estilo.LINEA, height=1)
