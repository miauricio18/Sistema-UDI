"""Administración: cargar datos, dar de alta laboratorios y cuidar la base.

Tiene tres pestañas. Cada una es una clase pequeña con su propia tarea, para
que dos personas puedan trabajar en pestañas distintas sin estorbarse.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable, List, Optional

from udi.modelos import Respaldo, ResumenImportacion

from .. import textos
from ..componentes.dialogos import Campo
from ..componentes.segmentos import Segmentos
from ..componentes.tabla import Columna, Fila, Tabla
from ..contexto import Contexto
from ..tema import Color, Estilo, Medida
from .base import Pantalla

_EXTENSIONES = (".csv", ".xlsx", ".xlsm")
_FILAS_BITACORA = 100


class _Pestana(ttk.Frame):
    """Molde de una pestaña: recibe el contexto y sabe actualizarse."""

    titulo = ""

    def __init__(self, padre: tk.Misc, contexto: Contexto) -> None:
        super().__init__(padre, padding=(0, Medida.MARGEN, 0, 0))
        self.contexto = contexto
        self.servicios = contexto.servicios
        self.construir()

    def construir(self) -> None:
        raise NotImplementedError

    def actualizar(self) -> None:
        """Vuelve a leer los datos de la pestaña."""


# --------------------------------------------------------------------------- #
# Datos: importar listas y horario
# --------------------------------------------------------------------------- #
class PestanaDatos(_Pestana):
    titulo = "Datos"

    def construir(self) -> None:
        self._opcion(
            "Lista de alumnos",
            "Archivo de Excel o CSV con las columnas: boleta, nombre, grupo. "
            "Si el grupo es nuevo, también materia y maestro.",
            "Importar lista", self.pedir_lista,
        )
        self._opcion(
            "Horario de clases",
            "Archivo de Excel o CSV con las columnas: fecha, hora, grupo, laboratorio. "
            "La hora de fin es opcional.",
            "Importar horario", self.pedir_horario,
        )
        ttk.Label(
            self, style=Estilo.SUAVE,
            text="Si una sola fila tiene un error no se guarda nada: se corrige el archivo "
                 "y se vuelve a importar. Importar dos veces el mismo archivo no duplica datos.",
            wraplength=720, justify="left",
        ).pack(anchor="w", pady=(Medida.MARGEN, 0))

    def _opcion(self, titulo: str, descripcion: str, texto_boton: str,
                accion: Callable[[], None]) -> None:
        fila = ttk.Frame(self)
        fila.pack(fill="x", pady=(0, Medida.MARGEN))
        ttk.Button(fila, text=texto_boton, command=accion, width=18).pack(side="right")
        ttk.Label(fila, text=titulo, style=Estilo.SUBTITULO).pack(anchor="w")
        ttk.Label(fila, text=descripcion, style=Estilo.SUAVE, wraplength=640,
                  justify="left").pack(anchor="w")

    def pedir_lista(self) -> None:
        ruta = self.contexto.elegir_archivo("Elegir la lista de alumnos", _EXTENSIONES)
        if ruta is not None:
            self.importar(self.servicios.archivos.importar_lista, ruta, "alumnos")

    def pedir_horario(self) -> None:
        ruta = self.contexto.elegir_archivo("Elegir el horario", _EXTENSIONES)
        if ruta is not None:
            self.importar(self.servicios.archivos.importar_horario, ruta, "clases")

    def importar(self, importador: Callable[[Path], ResumenImportacion], ruta: Path,
                 que: str) -> bool:
        resultado = self.contexto.intentar(lambda: importador(ruta))
        if not resultado.ok:
            return False
        resumen: ResumenImportacion = resultado.valor
        if resumen.fue_exitosa:
            self.contexto.avisos.exito(
                f"{ruta.name}: {resumen.agregados} {que} nuevos y "
                f"{resumen.actualizados} que ya estaban.")
            return True
        renglones = "\n".join(
            f"Fila {error.numero_fila}: {error.motivo}" for error in resumen.filas_con_error)
        self.contexto.avisos.error("No se importó nada: el archivo tiene filas con error.")
        self.contexto.mostrar_texto(
            "No se importó nada",
            f"Corrige estas filas en {ruta.name} y vuelve a importar:\n\n{renglones}")
        return False


# --------------------------------------------------------------------------- #
# Laboratorios
# --------------------------------------------------------------------------- #
class PestanaLaboratorios(_Pestana):
    titulo = "Laboratorios"

    def construir(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        barra = ttk.Frame(self)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, Medida.UNIDAD * 2))
        ttk.Label(
            barra, style=Estilo.SUAVE,
            text="Para agregar computadoras a un laboratorio, guárdalo otra vez con un total mayor.",
        ).pack(side="left")
        ttk.Button(barra, text="Agregar o cambiar laboratorio", style=Estilo.PRIMARIO,
                   command=self.pedir_laboratorio).pack(side="right")
        self._tabla = Tabla(
            self, (Columna("clave", "Clave", 140), Columna("nombre", "Nombre", 400, estira=True)))
        self._tabla.grid(row=1, column=0, sticky="nsew")

    def actualizar(self) -> None:
        self._tabla.cargar(
            Fila(l.id_laboratorio, (l.id_laboratorio, l.nombre))
            for l in self.servicios.laboratorios.listar()
        )

    def pedir_laboratorio(self) -> None:
        elegido = self._tabla.seleccion() or ""
        nombre = next((l.nombre for l in self.servicios.laboratorios.listar()
                       if l.id_laboratorio == elegido), "")
        datos = self.contexto.pedir_datos("Laboratorio", (
            Campo("clave", "Clave", elegido, ayuda="Corta y sin espacios, por ejemplo L1."),
            Campo("nombre", "Nombre", nombre, ayuda="Por ejemplo UDI 1."),
            Campo("total", "Número de computadoras", ayuda="Se numeran de 1 hasta este total."),
        ))
        if datos is not None:
            self.guardar_laboratorio(datos["clave"], datos["nombre"], datos["total"])

    def guardar_laboratorio(self, clave: str, nombre: str, total: str) -> bool:
        resultado = self.contexto.intentar(
            lambda: self.servicios.laboratorios.registrar_laboratorio(
                clave, nombre, textos.leer_entero(total, "El número de computadoras")),
            exito=f"Laboratorio {clave} guardado con {total} computadoras.")
        self.actualizar()
        return resultado.ok


# --------------------------------------------------------------------------- #
# Sistema: estado, respaldos y bitácora
# --------------------------------------------------------------------------- #
class PestanaSistema(_Pestana):
    titulo = "Sistema"

    def construir(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._estado = ttk.Label(self, justify="left")
        self._estado.grid(row=0, column=0, sticky="w")
        self._integridad = ttk.Label(self, justify="left")
        self._integridad.grid(row=1, column=0, sticky="w", pady=(4, 0))

        acciones = ttk.Frame(self)
        acciones.grid(row=2, column=0, sticky="ew", pady=Medida.UNIDAD * 2)
        ttk.Button(acciones, text="Respaldar ahora", style=Estilo.PRIMARIO,
                   command=self.respaldar).pack(side="left")
        ttk.Button(acciones, text="Restaurar un respaldo",
                   command=self.pedir_restauracion).pack(side="left", padx=Medida.UNIDAD)
        ttk.Label(acciones, text="Últimos cambios (bitácora)", style=Estilo.SUAVE).pack(side="right")

        self._bitacora = Tabla(
            self,
            (
                Columna("fecha", "Fecha", 150),
                Columna("accion", "Acción", 190),
                Columna("detalle", "Detalle", 400, estira=True),
            ),
            filas_visibles=6,
        )
        self._bitacora.grid(row=3, column=0, sticky="nsew")

    def actualizar(self) -> None:
        estado = self.servicios.mantenimiento.estado_sistema()
        self._estado.configure(text=(
            f"Versión {estado.version_aplicacion}    ·    "
            f"{estado.total_alumnos} alumnos    ·    {estado.total_clases} clases    ·    "
            f"Base de {textos.tamano(estado.tamano_bytes)}    ·    "
            f"{estado.total_respaldos} respaldos (último: {textos.fecha_hora(estado.ultimo_respaldo)})"
        ))
        if estado.integridad_ok:
            self._integridad.configure(text="✓ La base de datos está sana.", foreground=Color.EXITO)
        else:
            self._integridad.configure(
                text="! La base tiene problemas: " + "; ".join(estado.problemas_integridad)
                     + ". Conviene restaurar el respaldo más reciente.",
                foreground=Color.ERROR)
        self._bitacora.cargar(
            Fila(str(posicion), (textos.fecha_hora(r.fecha_hora), r.accion, r.detalle))
            for posicion, r in enumerate(self.servicios.mantenimiento.ver_bitacora(_FILAS_BITACORA))
        )

    def respaldar(self) -> Optional[Respaldo]:
        resultado = self.contexto.intentar(self.servicios.mantenimiento.respaldar_ahora)
        if resultado.ok:
            self.contexto.avisos.exito(f"Respaldo guardado: {resultado.valor.ruta.name}")
        self.actualizar()
        return resultado.valor

    def pedir_restauracion(self) -> None:
        respaldos: List[Respaldo] = self.servicios.mantenimiento.listar_respaldos()
        if not respaldos:
            self.contexto.avisos.info("Todavía no hay respaldos guardados.")
            return
        opciones = [f"{textos.fecha_hora(r.fecha)}  ·  {r.ruta.name}" for r in respaldos]
        datos = self.contexto.pedir_datos(
            "Restaurar un respaldo", (Campo("respaldo", "Respaldo", opciones[0], opciones),),
            texto_aceptar="Continuar")
        if datos is None:
            return
        elegido = respaldos[opciones.index(datos["respaldo"])]
        if self.contexto.confirmar(
            "Restaurar un respaldo",
            f"La base volverá a como estaba el {textos.fecha_hora(elegido.fecha)}. "
            "Todo lo registrado después se pierde. Antes se guarda una copia de lo actual.",
            texto_si="Restaurar", peligro=True,
        ):
            self.restaurar(elegido.ruta)

    def restaurar(self, ruta: Path) -> bool:
        resultado = self.contexto.intentar(
            lambda: self.servicios.mantenimiento.restaurar_respaldo(ruta),
            exito="Respaldo restaurado.")
        self.actualizar()
        return resultado.ok


# --------------------------------------------------------------------------- #
# La pantalla solo reúne las pestañas
# --------------------------------------------------------------------------- #
class PantallaAdministracion(Pantalla):
    clave = "administracion"
    titulo = "Administración"

    PESTANAS = (PestanaDatos, PestanaLaboratorios, PestanaSistema)

    def construir(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.encabezado(self).grid(row=0, column=0, sticky="ew", pady=(0, Medida.UNIDAD * 2))
        self._selector: Segmentos[int] = Segmentos(
            self, [(posicion, clase.titulo) for posicion, clase in enumerate(self.PESTANAS)],
            self.elegir_pestana)
        self._selector.grid(row=1, column=0, sticky="w")
        self.pestanas: List[_Pestana] = [clase(self, self.contexto) for clase in self.PESTANAS]
        self._visible = 0
        self.elegir_pestana(0)

    def al_mostrar(self) -> None:
        self.pestanas[self._visible].actualizar()

    def elegir_pestana(self, posicion: int) -> None:
        self.pestanas[self._visible].grid_remove()
        self._visible = posicion
        self._selector.marcar(posicion)
        self.pestanas[posicion].grid(row=2, column=0, sticky="nsew")
        self.pestanas[posicion].actualizar()

    def pestana(self, clase: type) -> _Pestana:
        """La pestaña de esa clase (la usan las pruebas)."""
        return next(p for p in self.pestanas if isinstance(p, clase))
