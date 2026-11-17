"""Ventana principal: menú lateral, área de pantallas y franja de avisos."""

from __future__ import annotations

import sys
import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Dict, Optional, Sequence, Type

from udi.aplicacion import Servicios

from . import textos
from .componentes import dialogos
from .componentes.avisos import BarraAvisos
from .contexto import Contexto
from .pantallas import PANTALLAS
from .pantallas.base import Pantalla
from .tema import Estilo, Medida, aplicar_tema

_MILISEGUNDOS_ENTRE_REVISIONES = 30_000
TITULO_VENTANA = "UDI · Asistencia y equipos"


class Aplicacion:
    """Arma la ventana y cambia de pantalla. No contiene reglas del sistema."""

    def __init__(
        self,
        servicios: Servicios,
        pantallas: Sequence[Type[Pantalla]] = PANTALLAS,
        raiz: Optional[tk.Tk] = None,
    ) -> None:
        self.raiz = raiz or tk.Tk()
        self._servicios = servicios
        self._clases: Dict[str, Type[Pantalla]] = {p.clave: p for p in pantallas}
        self._creadas: Dict[str, Pantalla] = {}
        self._botones: Dict[str, ttk.Button] = {}
        self._visible: Optional[str] = None

        self._preparar_ventana()
        self._construir_lateral()
        self._construir_contenido()
        self.contexto = Contexto(
            servicios=servicios,
            avisos=self.avisos,
            navegar=self.mostrar,
            confirmar=partial(dialogos.confirmar, self.raiz),
            elegir_archivo=partial(dialogos.elegir_archivo, self.raiz),
            pedir_datos=partial(dialogos.pedir_datos, self.raiz),
            mostrar_texto=partial(dialogos.mostrar_texto, self.raiz),
        )
        self.raiz.report_callback_exception = self._error_inesperado
        self.mostrar(pantallas[0].clave)
        self._revisar_tiempo()

    # -- uso -------------------------------------------------------------------
    def ejecutar(self) -> None:
        self.raiz.mainloop()

    def mostrar(self, clave: str) -> Pantalla:
        """Trae al frente la pantalla pedida y le pide que actualice sus datos."""
        pantalla = self.pantalla(clave)
        if self._visible is not None and self._visible != clave:
            self._creadas[self._visible].grid_remove()
            self.avisos.ocultar()   # un aviso habla de la pantalla que se deja
        pantalla.grid(row=0, column=0, sticky="nsew")
        self._visible = clave
        for otra, boton in self._botones.items():
            boton.configure(style=Estilo.NAV_ACTIVO if otra == clave else Estilo.NAV)
        pantalla.al_mostrar()
        return pantalla

    def pantalla(self, clave: str) -> Pantalla:
        """Las pantallas se crean hasta que se necesitan por primera vez."""
        if clave not in self._creadas:
            self._creadas[clave] = self._clases[clave](self._zona, self.contexto)
        return self._creadas[clave]

    # -- construcción ------------------------------------------------------------
    def _preparar_ventana(self) -> None:
        self.raiz.title(TITULO_VENTANA)
        self.raiz.geometry(Medida.VENTANA)
        self.raiz.minsize(*Medida.VENTANA_MINIMA)
        if sys.platform == "win32":
            self.raiz.state("zoomed")  # en la tableta abre a pantalla completa
        aplicar_tema(self.raiz)
        self.raiz.columnconfigure(1, weight=1)
        self.raiz.rowconfigure(0, weight=1)

    def _construir_lateral(self) -> None:
        lateral = ttk.Frame(self.raiz, style=Estilo.LATERAL, width=Medida.ANCHO_LATERAL,
                            padding=(Medida.UNIDAD * 2, Medida.MARGEN))
        lateral.grid(row=0, column=0, sticky="ns")
        lateral.pack_propagate(False)
        ttk.Label(lateral, text="UDI", style=Estilo.MARCA).pack(anchor="w", padx=Medida.UNIDAD)
        ttk.Label(lateral, text="Asistencia y equipos", style=Estilo.LATERAL_SUAVE).pack(
            anchor="w", padx=Medida.UNIDAD, pady=(0, Medida.MARGEN))
        for clave, clase in self._clases.items():
            boton = ttk.Button(lateral, text=clase.titulo, style=Estilo.NAV, takefocus=False,
                               command=partial(self.mostrar, clave))
            boton.pack(fill="x", pady=2)
            self._botones[clave] = boton
        self._reloj = ttk.Label(lateral, style=Estilo.LATERAL_SUAVE, justify="left",
                                wraplength=Medida.ANCHO_LATERAL - Medida.UNIDAD * 6)
        self._reloj.pack(side="bottom", anchor="w", padx=Medida.UNIDAD)

    def _construir_contenido(self) -> None:
        contenido = ttk.Frame(self.raiz)
        contenido.grid(row=0, column=1, sticky="nsew")
        contenido.rowconfigure(0, weight=1)
        contenido.columnconfigure(0, weight=1)
        self._zona = ttk.Frame(contenido)
        self._zona.grid(row=0, column=0, sticky="nsew")
        self._zona.rowconfigure(0, weight=1)
        self._zona.columnconfigure(0, weight=1)
        self.avisos = BarraAvisos(contenido)
        self.avisos.grid(row=1, column=0, sticky="ew")

    # -- tiempo y errores ----------------------------------------------------------
    def _revisar_tiempo(self) -> None:
        ahora = self._servicios.reloj.ahora()
        self._reloj.configure(text=f"{textos.fecha_larga(ahora.date())}\n{textos.hora(ahora)}")
        if self._visible is not None:
            self._creadas[self._visible].al_pasar_tiempo()
        self.raiz.after(_MILISEGUNDOS_ENTRE_REVISIONES, self._revisar_tiempo)

    def _error_inesperado(self, tipo, valor, traza) -> None:
        """Un error de programación no cierra la aplicación: se anota y se avisa."""
        self._servicios.logger.critical(
            "Error no controlado en la interfaz", exc_info=(tipo, valor, traza))
        self.avisos.error("Ocurrió un error inesperado. Quedó anotado en el registro (logs).")
