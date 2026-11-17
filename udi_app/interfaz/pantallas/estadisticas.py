"""Estadísticas: resumen por materia, asistencia por día de un grupo y exportación a Excel."""

from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import ttk
from typing import Dict, List, Optional

from udi.modelos import Grupo, Periodo

from .. import textos
from ..componentes.grafica import Barra, GraficaBarras
from ..componentes.tabla import Columna, Fila, Tabla
from ..tema import Estilo, Medida
from .base import Pantalla


class PantallaEstadisticas(Pantalla):
    clave = "estadisticas"
    titulo = "Estadísticas"

    def construir(self) -> None:
        self._periodos: Dict[str, Periodo] = {}
        self._grupos: List[Grupo] = []
        self._periodo = tk.StringVar(self)
        self._grupo = tk.StringVar(self)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)

        encabezado = self.encabezado(self)
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, Medida.UNIDAD * 2))
        ttk.Button(encabezado, text="Exportar a Excel", style=Estilo.PRIMARIO,
                   command=self.exportar).pack(side="right")
        self._selector_periodo = ttk.Combobox(
            encabezado, textvariable=self._periodo, state="readonly", width=24)
        self._selector_periodo.pack(side="right", padx=Medida.UNIDAD * 2)
        self._selector_periodo.bind("<<ComboboxSelected>>", lambda _evento: self.actualizar())
        ttk.Label(encabezado, text="Periodo", style=Estilo.SUAVE).pack(side="right")

        self._tabla = Tabla(
            self,
            (
                Columna("materia", "Materia", 300, estira=True),
                Columna("maestros", "Maestros", 100, alineacion="e"),
                Columna("grupos", "Grupos", 100, alineacion="e"),
                Columna("vinieron", "Grupos que vinieron", 170, alineacion="e"),
                Columna("alumnos", "Alumnos que asistieron", 190, alineacion="e"),
            ),
            filas_visibles=5,
        )
        self._tabla.grid(row=1, column=0, sticky="nsew")

        por_dia = ttk.Frame(self)
        por_dia.grid(row=2, column=0, sticky="ew", pady=(Medida.MARGEN, Medida.UNIDAD))
        ttk.Label(por_dia, text="Asistencia por día", style=Estilo.SUBTITULO).pack(side="left")
        self._selector_grupo = ttk.Combobox(
            por_dia, textvariable=self._grupo, state="readonly", width=44)
        self._selector_grupo.pack(side="right")
        self._selector_grupo.bind("<<ComboboxSelected>>", lambda _evento: self._pintar_grafica())
        ttk.Label(por_dia, text="Grupo", style=Estilo.SUAVE).pack(side="right", padx=Medida.UNIDAD)

        self._grafica = GraficaBarras(self)
        self._grafica.grid(row=3, column=0, sticky="nsew")

    # -- lectura y dibujo -------------------------------------------------------
    def al_mostrar(self) -> None:
        self._periodos = self._periodos_disponibles(self.hoy())
        self._selector_periodo.configure(values=list(self._periodos))
        if self._periodo.get() not in self._periodos:
            self._periodo.set(next(iter(self._periodos)))
        self._grupos = self.servicios.horario.listar_grupos()
        opciones = [f"{g.clave_grupo}  ·  {g.materia}" for g in self._grupos]
        self._selector_grupo.configure(values=opciones)
        if self._grupo.get() not in opciones:
            self._grupo.set(opciones[0] if opciones else "")
        self.actualizar()

    def actualizar(self) -> None:
        resumen = self.servicios.estadisticas.resumen_por_materia(self.periodo())
        self._tabla.cargar(
            Fila(str(posicion), (f.materia, f.maestros, f.grupos, f.grupos_que_vinieron, f.alumnos))
            for posicion, f in enumerate(resumen)
        )
        self._pintar_grafica()

    def _pintar_grafica(self) -> None:
        grupo = self.grupo_elegido()
        if grupo is None:
            self._grafica.cargar(())
            return
        dias = self.servicios.estadisticas.asistencia_por_dia(grupo.clave_grupo, self.periodo())
        self._grafica.cargar(
            [Barra(d.fecha.strftime("%d/%m"), d.asistieron, d.total) for d in dias])

    def periodo(self) -> Periodo:
        return self._periodos[self._periodo.get()]

    def grupo_elegido(self) -> Optional[Grupo]:
        posicion = self._selector_grupo.current()
        return self._grupos[posicion] if 0 <= posicion < len(self._grupos) else None

    @staticmethod
    def _periodos_disponibles(hoy: date) -> Dict[str, Periodo]:
        mes_anterior = hoy.replace(day=1) - timedelta(days=1)
        return {
            f"Este mes ({textos.nombre_mes(hoy)})": Periodo.de_mes(hoy.year, hoy.month),
            f"Mes anterior ({textos.nombre_mes(mes_anterior)})":
                Periodo.de_mes(mes_anterior.year, mes_anterior.month),
            "Este semestre": Periodo.semestre(hoy),
        }

    # -- acciones ---------------------------------------------------------------
    def exportar(self) -> Optional[Path]:
        resultado = self.contexto.intentar(
            lambda: self.servicios.archivos.exportar_excel(self.periodo()))
        if not resultado.ok:
            return None
        self.contexto.avisos.exito(f"Excel guardado en {resultado.valor}")
        return resultado.valor
