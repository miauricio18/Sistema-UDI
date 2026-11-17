"""Reportes: anotar una falla, una observación o un incidente, y consultar los anteriores."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from udi.modelos import Reporte, TipoReporte

from .. import textos
from ..componentes.dialogos import Campo
from ..componentes.segmentos import Segmentos
from ..componentes.tabla import Columna, Fila, Tabla
from ..tema import Color, Estilo, Medida, fuente
from .base import Pantalla

_ANCHO_FORMULARIO = 340
_OPCIONES_TIPO = (
    (TipoReporte.FALLA_EQUIPO, "Falla"),
    (TipoReporte.OBSERVACION, "Observación"),
    (TipoReporte.INCIDENTE, "Incidente"),
)


class PantallaReportes(Pantalla):
    clave = "reportes"
    titulo = "Reportes"

    def construir(self) -> None:
        self._reportes: List[Reporte] = []
        self._laboratorio = tk.StringVar(self)
        self._equipo = tk.StringVar(self)
        self._fuera = tk.BooleanVar(self, value=False)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        encabezado = self.encabezado(self)
        encabezado.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, Medida.UNIDAD * 2))
        ttk.Button(encabezado, text="Reactivar computadora",
                   command=self.pedir_reactivacion).pack(side="right")

        self._construir_formulario().grid(row=1, column=0, sticky="ns", padx=(0, Medida.MARGEN))
        self._construir_historial().grid(row=1, column=1, sticky="nsew")

    def _construir_formulario(self) -> ttk.Frame:
        marco = ttk.Frame(self, width=_ANCHO_FORMULARIO)
        ttk.Label(marco, text="Nuevo reporte", style=Estilo.SUBTITULO).pack(anchor="w")

        self._etiqueta(marco, "Tipo")
        self._tipo: Segmentos[TipoReporte] = Segmentos(marco, _OPCIONES_TIPO, self.elegir_tipo)
        self._tipo.pack(anchor="w")

        self._etiqueta(marco, "Laboratorio")
        self._selector_laboratorio = ttk.Combobox(
            marco, textvariable=self._laboratorio, state="readonly")
        self._selector_laboratorio.pack(fill="x")

        self._etiqueta(marco, "Computadora (número)")
        ttk.Entry(marco, textvariable=self._equipo).pack(fill="x")

        self._etiqueta(marco, "¿Qué pasó?")
        self._texto = tk.Text(marco, width=34, height=6, wrap="word", font=fuente(11),
                              relief="flat", borderwidth=0, padx=8, pady=8,
                              highlightthickness=1, highlightbackground=Color.BORDE,
                              highlightcolor=Color.ACENTO)
        self._texto.pack(fill="x")

        self._casilla = ttk.Checkbutton(
            marco, text="Dejar la computadora fuera de servicio", variable=self._fuera)
        self._casilla.pack(anchor="w", pady=(Medida.UNIDAD, 0))
        ttk.Button(marco, text="Guardar reporte", style=Estilo.PRIMARIO,
                   command=self.guardar_reporte).pack(fill="x", pady=(Medida.UNIDAD * 2, 0))
        self.elegir_tipo(TipoReporte.FALLA_EQUIPO)
        return marco

    def _construir_historial(self) -> ttk.Frame:
        marco = ttk.Frame(self)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(1, weight=1)
        ttk.Label(marco, text="Reportes anteriores", style=Estilo.SUBTITULO).grid(
            row=0, column=0, sticky="w", pady=(0, Medida.UNIDAD))
        self._tabla = Tabla(
            marco,
            (
                Columna("fecha", "Fecha", 136),
                Columna("tipo", "Tipo", 120),
                Columna("lugar", "Lugar", 64),
                Columna("texto", "Descripción", 150, estira=True),
                Columna("usuario", "Último alumno", 140),
            ),
            al_seleccionar=self._ver_reporte,
        )
        self._tabla.colorear(TipoReporte.FALLA_EQUIPO.value, texto=Color.ERROR)
        self._tabla.grid(row=1, column=0, sticky="nsew")
        self._detalle = ttk.Label(marco, style=Estilo.SUAVE, wraplength=640, justify="left")
        self._detalle.grid(row=2, column=0, sticky="ew", pady=(Medida.UNIDAD, 0))
        return marco

    @staticmethod
    def _etiqueta(padre: tk.Misc, texto: str) -> None:
        ttk.Label(padre, text=texto, style=Estilo.SUAVE).pack(
            anchor="w", pady=(Medida.UNIDAD * 2, 4))

    # -- lectura y dibujo -------------------------------------------------------
    def al_mostrar(self) -> None:
        laboratorios = [l.id_laboratorio for l in self.servicios.laboratorios.listar()]
        self._selector_laboratorio.configure(values=laboratorios)
        if self._laboratorio.get() not in laboratorios:
            self._laboratorio.set(laboratorios[0] if laboratorios else "")
        self.actualizar()

    def actualizar(self) -> None:
        self._reportes = self.servicios.reportes.listar_reportes()
        self._tabla.cargar(
            Fila(
                str(r.id_reporte),
                (textos.fecha_hora(r.fecha), textos.REPORTE[r.tipo], self._lugar(r),
                 r.texto, r.ultimo_usuario or ""),
                r.tipo.value,
            )
            for r in self._reportes
        )
        self._detalle.configure(text="" if self._reportes else "Todavía no hay reportes.")

    @staticmethod
    def _lugar(reporte: Reporte) -> str:
        if reporte.numero_equipo is None:
            return reporte.id_laboratorio
        return f"{reporte.id_laboratorio}-{reporte.numero_equipo}"

    def _ver_reporte(self, identificador: Optional[str]) -> None:
        reporte = next((r for r in self._reportes if str(r.id_reporte) == identificador), None)
        self._detalle.configure(text=reporte.texto if reporte else "")

    # -- acciones ---------------------------------------------------------------
    def elegir_tipo(self, tipo: TipoReporte) -> None:
        """Solo una falla de equipo puede dejar la computadora fuera de servicio."""
        self._tipo.marcar(tipo)
        es_falla = tipo is TipoReporte.FALLA_EQUIPO
        self._casilla.configure(state="normal" if es_falla else "disabled")
        self._fuera.set(es_falla)

    def guardar_reporte(self) -> bool:
        def guardar() -> Reporte:
            numero = self._equipo.get().strip()
            return self.servicios.reportes.crear_reporte(
                self._tipo.valor,
                self._laboratorio.get(),
                self._texto.get("1.0", "end").strip(),
                textos.leer_entero(numero, "La computadora") if numero else None,
                poner_fuera_de_servicio=self._fuera.get() and bool(numero),
            )

        resultado = self.contexto.intentar(guardar, exito="Reporte guardado.")
        if resultado.ok:
            self._texto.delete("1.0", "end")
            self._equipo.set("")
            self.actualizar()
        return resultado.ok

    def pedir_reactivacion(self) -> None:
        laboratorios = [l.id_laboratorio for l in self.servicios.laboratorios.listar()]
        if not laboratorios:
            self.contexto.avisos.info("Todavía no hay laboratorios dados de alta.")
            return
        datos = self.contexto.pedir_datos(
            "Reactivar computadora",
            (
                Campo("laboratorio", "Laboratorio", self._laboratorio.get() or laboratorios[0],
                      laboratorios),
                Campo("equipo", "Computadora (número)", ayuda="La que ya quedó reparada."),
            ),
            texto_aceptar="Reactivar",
        )
        if datos is not None:
            self.reactivar(datos["laboratorio"], datos["equipo"])

    def reactivar(self, laboratorio: str, numero: str) -> bool:
        resultado = self.contexto.intentar(
            lambda: self.servicios.reportes.reactivar_equipo(
                laboratorio, textos.leer_entero(numero, "La computadora")),
            exito=f"La computadora {numero} de {laboratorio} volvió a servicio.")
        return resultado.ok
