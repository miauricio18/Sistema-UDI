"""Pantalla principal: registrar llegadas y asignar computadoras.

Flujo normal: escribir la boleta, tocar «Registrar llegada» y tocar en el mapa
la computadora que usará el alumno. Tres toques por alumno.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional

from udi.modelos import (
    Asistencia,
    Equipo,
    EstadoAsistencia,
    EstadoMaestro,
    EstadoSesion,
    Origen,
    Sesion,
)

from .. import textos
from ..componentes.mapa_equipos import MapaEquipos
from ..componentes.segmentos import Segmentos
from ..componentes.tabla import Columna, Fila, Tabla
from ..componentes.teclado import TecladoNumerico
from ..tema import Color, Estilo, Medida, fuente
from .base import Pantalla

_OPCIONES_MAESTRO = (
    (EstadoMaestro.VINO, "Vino"),
    (EstadoMaestro.NO_VINO, "No vino"),
    (EstadoMaestro.AVISO, "Avisó"),
)
_COLOR_ESTADO = {
    EstadoAsistencia.PENDIENTE: Color.TEXTO_SUAVE,
    EstadoAsistencia.LLEGO: Color.EXITO,
    EstadoAsistencia.RETARDO: Color.ALERTA,
    EstadoAsistencia.FALTA: Color.ERROR,
}
_SIN_ALUMNO = "Ninguno. Registra una boleta o toca un nombre de la lista."


class PantallaPaseLista(Pantalla):
    clave = "pase_lista"
    titulo = "Pase de lista"

    # ------------------------------------------------------------------ #
    # Construcción
    # ------------------------------------------------------------------ #
    def construir(self) -> None:
        self._sesion: Optional[Sesion] = None
        self._clase_fijada: Optional[int] = None   # clase elegida a mano en la lista
        self._clases_del_dia: List[Sesion] = []
        self._lista: List[Asistencia] = []
        self._equipos: List[Equipo] = []
        self._boleta_elegida: Optional[str] = None
        self._boleta = tk.StringVar(self)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._construir_encabezado().grid(row=0, column=0, sticky="ew")
        self._clase = self._construir_clase()
        self._clase.grid(row=1, column=0, sticky="ew", pady=(Medida.UNIDAD * 2, 0))
        self._cuerpo = self._construir_cuerpo()
        self._cuerpo.grid(row=2, column=0, sticky="nsew", pady=(Medida.UNIDAD * 2, 0))
        self._vacio = self._construir_vacio()

    def _construir_encabezado(self) -> ttk.Frame:
        marco = self.encabezado(self)
        self._selector = ttk.Combobox(marco, state="readonly", width=46)
        self._selector.pack(side="right")
        self._selector.bind("<<ComboboxSelected>>", self._al_elegir_en_selector)
        ttk.Label(marco, text="Clase", style=Estilo.SUAVE).pack(side="right", padx=Medida.UNIDAD)
        return marco

    def _construir_clase(self) -> ttk.Frame:
        marco = ttk.Frame(self)
        marco.columnconfigure(0, weight=1)
        self._materia = ttk.Label(marco, style=Estilo.DESTACADO)
        self._materia.grid(row=0, column=0, sticky="w")
        self._detalle_clase = ttk.Label(marco, style=Estilo.SUAVE)
        self._detalle_clase.grid(row=1, column=0, sticky="w")
        ttk.Label(marco, text="Maestro", style=Estilo.SUAVE).grid(
            row=0, column=1, rowspan=2, padx=Medida.UNIDAD)
        self._maestro: Segmentos[EstadoMaestro] = Segmentos(
            marco, _OPCIONES_MAESTRO, self.marcar_maestro)
        self._maestro.grid(row=0, column=2, rowspan=2)
        self.linea(marco).grid(row=2, column=0, columnspan=3, sticky="ew",
                               pady=(Medida.UNIDAD * 2, 0))
        return marco

    def _construir_cuerpo(self) -> ttk.Frame:
        marco = ttk.Frame(self)
        marco.columnconfigure(0, minsize=Medida.ANCHO_PANEL)
        marco.columnconfigure(1, weight=1)
        marco.rowconfigure(0, weight=1)
        self._construir_captura(marco).grid(row=0, column=0, sticky="nsew",
                                            padx=(0, Medida.MARGEN))
        self._construir_laboratorio(marco).grid(row=0, column=1, sticky="nsew")
        return marco

    def _construir_captura(self, padre: tk.Misc) -> ttk.Frame:
        marco = ttk.Frame(padre)
        ttk.Label(marco, text="Boleta", style=Estilo.SUAVE).pack(anchor="w")
        self._entrada = ttk.Entry(marco, textvariable=self._boleta, font=fuente(18),
                                  style=Estilo.ENTRADA_GRANDE, width=14)
        self._entrada.pack(fill="x", pady=(4, Medida.UNIDAD))
        self._entrada.bind("<Return>", lambda _evento: self.registrar_llegada())
        TecladoNumerico(marco, self._boleta).pack(fill="x")
        ttk.Button(marco, text="Registrar llegada", style=Estilo.PRIMARIO,
                   command=self.registrar_llegada).pack(fill="x", pady=(Medida.UNIDAD, 0))

        ttk.Label(marco, text="Alumno seleccionado", style=Estilo.SUAVE).pack(
            anchor="w", pady=(Medida.MARGEN, 0))
        self._nombre = ttk.Label(marco, style=Estilo.SUBTITULO,
                                 wraplength=Medida.ANCHO_PANEL, justify="left")
        self._nombre.pack(anchor="w", fill="x")
        self._detalle_alumno = ttk.Label(marco, style=Estilo.SUAVE,
                                         wraplength=Medida.ANCHO_PANEL, justify="left")
        self._detalle_alumno.pack(anchor="w", fill="x")
        acciones = ttk.Frame(marco)
        acciones.pack(fill="x", pady=(Medida.UNIDAD, 0))
        acciones.columnconfigure((0, 1), weight=1, uniform="accion")
        self._boton_laptop = ttk.Button(acciones, text="Trae laptop", command=self.alternar_laptop)
        self._boton_laptop.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._boton_liberar = ttk.Button(acciones, text="Quitar equipo", command=self.liberar_equipo)
        self._boton_liberar.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        return marco

    def _construir_laboratorio(self, padre: tk.Misc) -> ttk.Frame:
        marco = ttk.Frame(padre)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(3, weight=1)
        titulo = ttk.Frame(marco)
        titulo.grid(row=0, column=0, sticky="ew")
        ttk.Label(titulo, text="Computadoras", style=Estilo.SUBTITULO).pack(side="left")
        ttk.Label(titulo, text="Toca una libre para asignarla.",
                  style=Estilo.SUAVE).pack(side="left", padx=Medida.UNIDAD * 2)
        self._mapa = MapaEquipos(marco, self.tocar_equipo)
        self._mapa.grid(row=1, column=0, sticky="ew", pady=(Medida.UNIDAD, Medida.UNIDAD * 2))

        lista = ttk.Frame(marco)
        lista.grid(row=2, column=0, sticky="ew", pady=(0, Medida.UNIDAD))
        ttk.Label(lista, text="Lista del grupo", style=Estilo.SUBTITULO).pack(side="left")
        self._conteo = ttk.Label(lista, style=Estilo.SUAVE)
        self._conteo.pack(side="left", padx=Medida.UNIDAD * 2)
        self._boton_cierre = ttk.Button(lista)
        self._boton_cierre.pack(side="right")
        self._tabla = Tabla(
            marco,
            (
                Columna("boleta", "Boleta", 120),
                Columna("nombre", "Nombre", 220, estira=True),
                Columna("estado", "Estado", 100),
                Columna("llegada", "Llegada", 80),
                Columna("equipo", "Equipo", 90),
            ),
            al_seleccionar=self.seleccionar_alumno,
            filas_visibles=5,
        )
        for estado, color in _COLOR_ESTADO.items():
            self._tabla.colorear(estado.value, texto=color)
        self._tabla.grid(row=3, column=0, sticky="nsew")
        return marco

    def _construir_vacio(self) -> ttk.Frame:
        marco = ttk.Frame(self)
        ttk.Label(marco, text="No hay clases hoy", style=Estilo.DESTACADO).pack(pady=(96, 4))
        ttk.Label(marco, text="Cuando haya una clase en el horario aparecerá aquí.",
                  style=Estilo.SUAVE).pack()
        ttk.Button(marco, text="Ver horario", style=Estilo.PRIMARIO,
                   command=lambda: self.contexto.navegar("horario")).pack(pady=Medida.MARGEN)
        return marco

    # ------------------------------------------------------------------ #
    # Lectura de datos
    # ------------------------------------------------------------------ #
    def al_mostrar(self) -> None:
        self.actualizar()
        self._entrada.focus_set()

    def al_pasar_tiempo(self) -> None:
        """Pasa sola a la clase siguiente, sin interrumpir si se está escribiendo."""
        fijada = self._sesion if self._clase_fijada is not None else None
        if fijada is not None and fijada.estado is EstadoSesion.CERRADA:
            if self.servicios.reloj.ahora() >= fijada.hora_fin:
                self._clase_fijada = None
        if not self._boleta.get():
            self.actualizar()

    def actualizar(self) -> None:
        self._clases_del_dia = self.servicios.horario.listar_dia(self.hoy())
        self._sesion = self._clase_por_mostrar()
        self._pintar_selector()
        if self._sesion is None:
            self._alternar_vacio(True)
            return
        self._alternar_vacio(False)
        id_sesion = self._sesion.id_sesion
        self._lista = self.servicios.asistencia.obtener_lista(id_sesion)
        self._equipos = self.servicios.asistencia.mapa_laboratorio(id_sesion)
        if self._asistencia_elegida() is None:
            self._boleta_elegida = None
        self._pintar_clase()
        self._pintar_laboratorio()
        self._pintar_alumno()
        self._pintar_cierre()

    def _clase_por_mostrar(self) -> Optional[Sesion]:
        if self._clase_fijada is not None:
            for sesion in self._clases_del_dia:
                if sesion.id_sesion == self._clase_fijada:
                    return sesion
            self._clase_fijada = None
        actual = self.contexto.intentar(
            self.servicios.asistencia.obtener_sesion_actual, avisar=False)
        if actual.ok:
            return actual.valor
        # Todas las clases del día ya se cerraron: se muestra la última, por si hay que reabrirla.
        return self._clases_del_dia[-1] if self._clases_del_dia else None

    def _asistencia_elegida(self) -> Optional[Asistencia]:
        for asistencia in self._lista:
            if asistencia.alumno.boleta == self._boleta_elegida:
                return asistencia
        return None

    # ------------------------------------------------------------------ #
    # Dibujo
    # ------------------------------------------------------------------ #
    def _alternar_vacio(self, vacio: bool) -> None:
        for parte in (self._clase, self._cuerpo):
            parte.grid_remove() if vacio else parte.grid()
        if vacio:
            self._vacio.grid(row=1, column=0, rowspan=2, sticky="nsew")
        else:
            self._vacio.grid_remove()

    def _pintar_selector(self) -> None:
        self._selector.configure(values=[textos.resumen_clase(s) for s in self._clases_del_dia])
        if self._sesion is None:
            self._selector.set("")
            return
        for posicion, sesion in enumerate(self._clases_del_dia):
            if sesion.id_sesion == self._sesion.id_sesion:
                self._selector.current(posicion)

    def _pintar_clase(self) -> None:
        sesion = self._sesion
        assert sesion is not None
        grupo = sesion.grupo
        self._materia.configure(text=grupo.materia)
        self._detalle_clase.configure(
            text=f"Grupo {grupo.clave_grupo}  ·  Laboratorio {sesion.id_laboratorio}  ·  "
                 f"{textos.horario_clase(sesion)}  ·  {grupo.maestro}  ·  "
                 f"{textos.SESION[sesion.estado]}")
        self._maestro.marcar(sesion.estado_maestro)

    def _pintar_laboratorio(self) -> None:
        elegida = self._asistencia_elegida()
        self._mapa.cargar(self._equipos, elegida.numero_equipo if elegida else None)
        self._tabla.cargar(
            (
                Fila(
                    a.alumno.boleta,
                    (a.alumno.boleta, a.alumno.nombre, textos.ASISTENCIA[a.estado],
                     textos.hora(a.hora_llegada), self._texto_equipo(a)),
                    a.estado.value,
                )
                for a in self._lista
            ),
            seleccion=self._boleta_elegida,
        )

    def _pintar_alumno(self) -> None:
        elegida = self._asistencia_elegida()
        estado = "normal" if elegida is not None else "disabled"
        self._boton_laptop.configure(
            state=estado, text="Quitar laptop" if elegida and elegida.es_laptop else "Trae laptop")
        self._boton_liberar.configure(
            state="normal" if elegida and elegida.numero_equipo else "disabled")
        if elegida is None:
            self._nombre.configure(text="")
            self._detalle_alumno.configure(text=_SIN_ALUMNO)
            return
        partes = [elegida.alumno.boleta, textos.ASISTENCIA[elegida.estado]]
        if elegida.hora_llegada:
            partes.append(textos.hora(elegida.hora_llegada))
        partes.append(self._texto_equipo(elegida, largo=True))
        self._nombre.configure(text=elegida.alumno.nombre)
        self._detalle_alumno.configure(text="  ·  ".join(partes))

    def _pintar_cierre(self) -> None:
        sesion = self._sesion
        assert sesion is not None
        cuenta: Dict[EstadoAsistencia, int] = {estado: 0 for estado in EstadoAsistencia}
        for asistencia in self._lista:
            cuenta[asistencia.estado] += 1
        self._conteo.configure(text="   ·   ".join(
            f"{textos.ASISTENCIA[estado]}: {total}"
            for estado, total in cuenta.items()
            if total or estado is not EstadoAsistencia.FALTA
        ))
        if sesion.estado is EstadoSesion.CERRADA:
            self._boton_cierre.configure(text="Reabrir pase de lista", style=Estilo.BOTON,
                                         command=self.reabrir_pase)
        else:
            self._boton_cierre.configure(text="Terminar pase de lista", style=Estilo.PRIMARIO,
                                         command=self.terminar_pase)

    @staticmethod
    def _texto_equipo(asistencia: Asistencia, largo: bool = False) -> str:
        if asistencia.es_laptop:
            return "Laptop propia" if largo else "Laptop"
        if asistencia.numero_equipo:
            return f"Computadora {asistencia.numero_equipo}" if largo else str(asistencia.numero_equipo)
        return "Sin equipo" if largo else ""

    # ------------------------------------------------------------------ #
    # Acciones (cada una llama a un servicio y vuelve a leer)
    # ------------------------------------------------------------------ #
    def elegir_clase(self, id_sesion: int) -> None:
        self._clase_fijada = id_sesion
        self._boleta_elegida = None
        self.actualizar()

    def seleccionar_alumno(self, boleta: Optional[str]) -> None:
        self._boleta_elegida = boleta
        self._pintar_laboratorio()
        self._pintar_alumno()

    def registrar_llegada(self) -> None:
        """Con boleta escrita registra esa; si no, al alumno seleccionado en la lista."""
        if self._sesion is None:
            return
        escrita = self._boleta.get().strip()
        boleta = escrita or self._boleta_elegida
        if not boleta:
            self.contexto.avisos.info("Escribe la boleta o toca un nombre de la lista.")
            return
        origen = Origen.TABLETA if escrita else Origen.MANUAL
        resultado = self.contexto.intentar(
            lambda: self.servicios.asistencia.registrar_llegada(
                self._sesion.id_sesion, boleta, origen))
        if resultado.ok:
            asistencia: Asistencia = resultado.valor
            self._boleta.set("")
            self._boleta_elegida = asistencia.alumno.boleta
            retardo = " con retardo" if asistencia.es_retardo else ""
            self.contexto.avisos.exito(
                f"{asistencia.alumno.nombre}: llegada registrada{retardo}. "
                "Toca su computadora en el mapa.")
        self.actualizar()

    def tocar_equipo(self, numero: int) -> None:
        if self._sesion is None:
            return
        elegida = self._asistencia_elegida()
        if elegida is None:
            ocupante = next((e.alumno_actual for e in self._equipos if e.numero == numero), None)
            if ocupante is not None:
                self.seleccionar_alumno(ocupante.boleta)
            else:
                self.contexto.avisos.info("Primero registra una boleta o toca un nombre de la lista.")
            return
        resultado = self.contexto.intentar(
            lambda: self.servicios.asistencia.asignar_equipo(
                self._sesion.id_sesion, elegida.alumno.boleta, numero),
            exito=f"Computadora {numero} asignada a {elegida.alumno.nombre}.")
        if resultado.ok:
            self._boleta_elegida = None   # ese alumno ya quedó listo: sigue el próximo
            self._entrada.focus_set()
        self.actualizar()

    def alternar_laptop(self) -> None:
        elegida = self._asistencia_elegida()
        if self._sesion is None or elegida is None:
            return
        trae = not elegida.es_laptop
        self.contexto.intentar(
            lambda: self.servicios.asistencia.marcar_laptop(
                self._sesion.id_sesion, elegida.alumno.boleta, trae),
            exito=f"{elegida.alumno.nombre}: " + ("trae laptop propia." if trae else "ya no usa laptop."))
        self.actualizar()

    def liberar_equipo(self) -> None:
        elegida = self._asistencia_elegida()
        if self._sesion is None or elegida is None:
            return
        self.contexto.intentar(
            lambda: self.servicios.asistencia.liberar_equipo(
                self._sesion.id_sesion, elegida.alumno.boleta),
            exito=f"{elegida.alumno.nombre} ya no tiene computadora asignada.")
        self.actualizar()

    def marcar_maestro(self, estado: EstadoMaestro) -> None:
        if self._sesion is None:
            return
        self.contexto.intentar(
            lambda: self.servicios.maestros.marcar_maestro(self._sesion.id_sesion, estado),
            exito=f"Maestro: {textos.MAESTRO[estado].lower()}.")
        self.actualizar()

    def terminar_pase(self) -> None:
        if self._sesion is None:
            return
        pendientes = sum(1 for a in self._lista if a.estado is EstadoAsistencia.PENDIENTE)
        if not self.contexto.confirmar(
            "Terminar pase de lista",
            f"Los {pendientes} alumnos pendientes quedarán con falta. "
            "Si te equivocas, después puedes reabrir el pase.",
            texto_si="Terminar",
        ):
            return
        id_sesion = self._sesion.id_sesion
        resultado = self.contexto.intentar(
            lambda: self.servicios.asistencia.terminar_pase_lista(id_sesion),
            exito="Pase de lista terminado. Se guardó un respaldo.")
        if resultado.ok:
            self._clase_fijada = id_sesion   # se queda a la vista para revisar o reabrir
        self.actualizar()

    def reabrir_pase(self) -> None:
        if self._sesion is None:
            return
        self.contexto.intentar(
            lambda: self.servicios.asistencia.reabrir_pase_lista(self._sesion.id_sesion),
            exito="Pase de lista reabierto. Las faltas volvieron a pendientes.")
        self.actualizar()

    def _al_elegir_en_selector(self, _evento: tk.Event) -> None:
        posicion = self._selector.current()
        if 0 <= posicion < len(self._clases_del_dia):
            self.elegir_clase(self._clases_del_dia[posicion].id_sesion)
        self._selector.selection_clear()
