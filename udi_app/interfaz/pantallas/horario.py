"""Horario: ver las clases de un día y crear, cambiar o cancelar una."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from tkinter import ttk
from typing import Dict, List, Optional

from udi.modelos import EstadoSesion, Sesion

from .. import textos
from ..componentes.dialogos import Campo
from ..componentes.tabla import Columna, Fila, Tabla
from ..tema import Color, Estilo, Medida
from .base import Pantalla

_SEPARADOR = "  ·  "


class PantallaHorario(Pantalla):
    clave = "horario"
    titulo = "Horario"

    def construir(self) -> None:
        self._dia: date = self.hoy()
        self._clases: List[Sesion] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        encabezado = self.encabezado(self)
        encabezado.grid(row=0, column=0, sticky="ew")
        ttk.Button(encabezado, text="Nueva clase", style=Estilo.PRIMARIO,
                   command=self.nueva_clase).pack(side="right")

        dias = ttk.Frame(self)
        dias.grid(row=1, column=0, sticky="ew", pady=Medida.UNIDAD * 2)
        ttk.Button(dias, text="◀", width=3, command=lambda: self.cambiar_dia(-1)).pack(side="left")
        ttk.Button(dias, text="Hoy", command=self.ir_a_hoy).pack(side="left", padx=4)
        ttk.Button(dias, text="▶", width=3, command=lambda: self.cambiar_dia(1)).pack(side="left")
        self._fecha = ttk.Label(dias, style=Estilo.SUBTITULO)
        self._fecha.pack(side="left", padx=Medida.UNIDAD * 2)

        self._tabla = Tabla(
            self,
            (
                Columna("hora", "Hora", 120),
                Columna("materia", "Materia", 260, estira=True),
                Columna("grupo", "Grupo", 90),
                Columna("maestro", "Maestro", 200),
                Columna("laboratorio", "Laboratorio", 110),
                Columna("estado", "Estado", 110),
            ),
            al_seleccionar=lambda _id: self._pintar_acciones(),
            filas_visibles=10,
        )
        self._tabla.colorear(EstadoSesion.CERRADA.value, texto=Color.TEXTO_SUAVE)
        self._tabla.colorear(EstadoSesion.EN_CURSO.value, texto=Color.EXITO)
        self._tabla.grid(row=2, column=0, sticky="nsew")

        pie = ttk.Frame(self)
        pie.grid(row=3, column=0, sticky="ew", pady=(Medida.UNIDAD * 2, 0))
        self._ayuda = ttk.Label(pie, style=Estilo.SUAVE)
        self._ayuda.pack(side="left")
        self._boton_cancelar = ttk.Button(pie, text="Cancelar clase", style=Estilo.PELIGRO,
                                          command=self.cancelar_clase)
        self._boton_cancelar.pack(side="right")
        self._boton_editar = ttk.Button(pie, text="Cambiar", command=self.editar_clase)
        self._boton_editar.pack(side="right", padx=Medida.UNIDAD)

    # -- lectura y dibujo -------------------------------------------------------
    def al_mostrar(self) -> None:
        self.actualizar()

    def actualizar(self) -> None:
        self._clases = self.servicios.horario.listar_dia(self._dia)
        self._fecha.configure(text=textos.fecha_larga(self._dia))
        self._tabla.cargar(
            Fila(
                str(s.id_sesion),
                (textos.horario_clase(s), s.grupo.materia, s.grupo.clave_grupo,
                 s.grupo.maestro, s.id_laboratorio, textos.SESION[s.estado]),
                s.estado.value,
            )
            for s in self._clases
        )
        self._pintar_acciones()

    def _pintar_acciones(self) -> None:
        elegida = self.clase_elegida()
        modificable = elegida is not None and elegida.estado is not EstadoSesion.CERRADA
        for boton in (self._boton_editar, self._boton_cancelar):
            boton.configure(state="normal" if modificable else "disabled")
        if not self._clases:
            self._ayuda.configure(text="No hay clases este día.")
        elif elegida is None:
            self._ayuda.configure(text="Toca una clase para cambiarla o cancelarla.")
        elif not modificable:
            self._ayuda.configure(text="Una clase cerrada ya no se puede cambiar.")
        else:
            self._ayuda.configure(text="")

    def clase_elegida(self) -> Optional[Sesion]:
        identificador = self._tabla.seleccion()
        return next((s for s in self._clases if str(s.id_sesion) == identificador), None)

    # -- acciones ---------------------------------------------------------------
    def cambiar_dia(self, dias: int) -> None:
        self._dia += timedelta(days=dias)
        self.actualizar()

    def ir_a_hoy(self) -> None:
        self._dia = self.hoy()
        self.actualizar()

    def nueva_clase(self) -> None:
        datos = self._pedir_clase("Nueva clase", None)
        if datos is not None:
            self.guardar_clase(datos)

    def editar_clase(self) -> None:
        elegida = self.clase_elegida()
        if elegida is None:
            return
        datos = self._pedir_clase("Cambiar clase", elegida)
        if datos is not None:
            self.guardar_clase(datos, elegida.id_sesion)

    def guardar_clase(self, datos: Dict[str, str], id_sesion: Optional[int] = None) -> bool:
        """Crea la clase, o cambia la que tiene ``id_sesion``. ``datos`` viene del formulario."""
        def guardar() -> Sesion:
            dia = textos.leer_fecha(datos["fecha"])
            inicio = datetime.combine(dia, textos.leer_hora(datos["inicio"]))
            fin = datetime.combine(dia, textos.leer_hora(datos["fin"])) if datos.get("fin") else None
            grupo = datos["grupo"].split(_SEPARADOR)[0]
            laboratorio = datos["laboratorio"].split(_SEPARADOR)[0]
            if id_sesion is None:
                return self.servicios.horario.crear_clase(grupo, laboratorio, inicio, fin)
            return self.servicios.horario.editar_clase(id_sesion, grupo, laboratorio, inicio, fin)

        resultado = self.contexto.intentar(guardar, exito="Clase guardada.")
        if resultado.ok:
            self._dia = resultado.valor.hora_inicio.date()
            self.actualizar()
        return resultado.ok

    def cancelar_clase(self) -> None:
        elegida = self.clase_elegida()
        if elegida is None:
            return
        if not self.contexto.confirmar(
            "Cancelar clase",
            f"Se cancelará {elegida.grupo.materia} ({elegida.grupo.clave_grupo}) de las "
            f"{textos.hora(elegida.hora_inicio)}. Dejará de aparecer en el horario.",
            texto_si="Cancelar clase", peligro=True,
        ):
            return
        self.contexto.intentar(
            lambda: self.servicios.horario.cancelar_clase(elegida.id_sesion),
            exito="Clase cancelada.")
        self.actualizar()

    # -- formulario ---------------------------------------------------------------
    def _pedir_clase(self, titulo: str, clase: Optional[Sesion]) -> Optional[Dict[str, str]]:
        grupos = [f"{g.clave_grupo}{_SEPARADOR}{g.materia}"
                  for g in self.servicios.horario.listar_grupos()]
        laboratorios = [f"{l.id_laboratorio}{_SEPARADOR}{l.nombre}"
                        for l in self.servicios.horario.listar_laboratorios()]
        if not grupos or not laboratorios:
            self.contexto.avisos.info(
                "Antes hay que dar de alta laboratorios e importar una lista (Administración).")
            return None
        return self.contexto.pedir_datos(titulo, (
            Campo("grupo", "Grupo", self._opcion(grupos, clase.grupo.clave_grupo if clase else None),
                  grupos),
            Campo("laboratorio", "Laboratorio",
                  self._opcion(laboratorios, clase.id_laboratorio if clase else None), laboratorios),
            Campo("fecha", "Fecha", textos.fecha_corta(clase.hora_inicio.date() if clase else self._dia),
                  ayuda="día/mes/año"),
            Campo("inicio", "Hora de inicio", textos.hora(clase.hora_inicio) if clase else "",
                  ayuda="24 horas, por ejemplo 07:00"),
            Campo("fin", "Hora de fin (opcional)", textos.hora(clase.hora_fin) if clase else "",
                  ayuda="Si se deja vacía, la clase dura 90 minutos."),
        ))

    @staticmethod
    def _opcion(opciones: List[str], clave: Optional[str]) -> str:
        """La opción que empieza con esa clave; si no hay clave, la primera."""
        for opcion in opciones:
            if clave is not None and opcion.split(_SEPARADOR)[0] == clave:
                return opcion
        return opciones[0]
