"""Punto de arranque del backend: arma todas las piezas y las entrega a la interfaz.

La interfaz solo hace::

    from udi.aplicacion import iniciar
    servicios = iniciar()                    # datos reales
    servicios = iniciar(datos_ejemplo=True)  # datos ficticios en memoria
    servicios.asistencia.obtener_sesion_actual()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from . import __version__
from .auditoria import Auditoria
from .base_datos import BaseDatos
from .configuracion import Configuracion, Reloj
from .datos_ejemplo import cargar_datos_ejemplo
from .registro import configurar_registro, instalar_gancho_errores
from .repositorio import (
    RepositorioAlumnos,
    RepositorioAsistencias,
    RepositorioBitacora,
    RepositorioEquipos,
    RepositorioGrupos,
    RepositorioLaboratorios,
    RepositorioReportes,
    RepositorioSesiones,
    RepositorioUsos,
)
from .respaldos import GestorRespaldos
from .servicios.archivos import ServicioArchivos
from .servicios.asistencia import ServicioAsistencia
from .servicios.estadisticas import ServicioEstadisticas
from .servicios.horario import ServicioHorario
from .servicios.laboratorios import ServicioLaboratorios
from .servicios.maestros import ServicioMaestros
from .servicios.mantenimiento import ServicioMantenimiento
from .servicios.reportes import ServicioReportes


@dataclass
class Servicios:
    """Todo lo que la interfaz necesita, en un solo objeto."""

    asistencia: ServicioAsistencia
    maestros: ServicioMaestros
    reportes: ServicioReportes
    horario: ServicioHorario
    laboratorios: ServicioLaboratorios
    estadisticas: ServicioEstadisticas
    archivos: ServicioArchivos
    mantenimiento: ServicioMantenimiento
    base_datos: BaseDatos
    reloj: Reloj
    logger: logging.Logger

    def cerrar(self) -> None:
        """Cierra la base de datos. Llamar al salir de la aplicación."""
        self.logger.info("Aplicación cerrada")
        self.base_datos.cerrar()


def iniciar(
    configuracion: Optional[Configuracion] = None,
    datos_ejemplo: bool = False,
    reloj: Optional[Reloj] = None,
) -> Servicios:
    """Crea la base (si hace falta) y conecta repositorios con servicios.

    ``reloj`` solo se pasa en las pruebas, para controlar la hora.
    """
    if configuracion is None:
        configuracion = Configuracion.para_memoria() if datos_ejemplo else Configuracion()
    reloj = reloj or Reloj()

    logger = configurar_registro(configuracion)
    instalar_gancho_errores(logger)

    base_datos = BaseDatos(configuracion)
    base_datos.crear_tablas()
    logger.info(
        "Aplicación iniciada version=%s esquema=%s base=%s",
        __version__, base_datos.version_esquema, configuracion.ruta_bd,
    )

    alumnos = RepositorioAlumnos(base_datos)
    grupos = RepositorioGrupos(base_datos)
    laboratorios = RepositorioLaboratorios(base_datos)
    sesiones = RepositorioSesiones(base_datos)
    equipos = RepositorioEquipos(base_datos)
    asistencias = RepositorioAsistencias(base_datos)
    usos = RepositorioUsos(base_datos)
    reportes = RepositorioReportes(base_datos)
    bitacora = RepositorioBitacora(base_datos)

    auditoria = Auditoria(bitacora, reloj, logger)
    respaldos = GestorRespaldos(base_datos, configuracion, reloj, logger)

    if datos_ejemplo:
        cargar_datos_ejemplo(base_datos, reloj.ahora(), configuracion.minutos_clase)

    estadisticas = ServicioEstadisticas(asistencias)
    return Servicios(
        asistencia=ServicioAsistencia(
            base_datos=base_datos,
            configuracion=configuracion,
            reloj=reloj,
            alumnos=alumnos,
            sesiones=sesiones,
            equipos=equipos,
            asistencias=asistencias,
            usos=usos,
            respaldos=respaldos,
            auditoria=auditoria,
        ),
        maestros=ServicioMaestros(base_datos, sesiones, auditoria),
        reportes=ServicioReportes(
            base_datos, configuracion, reloj, reportes, laboratorios, equipos, usos, auditoria
        ),
        horario=ServicioHorario(
            base_datos=base_datos,
            configuracion=configuracion,
            reloj=reloj,
            sesiones=sesiones,
            grupos=grupos,
            laboratorios=laboratorios,
            auditoria=auditoria,
        ),
        laboratorios=ServicioLaboratorios(base_datos, laboratorios, equipos, auditoria),
        estadisticas=estadisticas,
        archivos=ServicioArchivos(
            base_datos=base_datos,
            configuracion=configuracion,
            reloj=reloj,
            alumnos=alumnos,
            grupos=grupos,
            laboratorios=laboratorios,
            sesiones=sesiones,
            asistencias=asistencias,
            auditoria=auditoria,
            estadisticas=estadisticas,
        ),
        mantenimiento=ServicioMantenimiento(
            base_datos, configuracion, respaldos, alumnos, sesiones, bitacora, auditoria
        ),
        base_datos=base_datos,
        reloj=reloj,
        logger=logger,
    )
