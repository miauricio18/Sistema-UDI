"""Datos que viajan entre capas: clases de datos y estados.

Aquí no hay lógica de negocio. Son las "cajas" que la interfaz recibe de los
servicios. Los estados se piden siempre con los Enum, nunca con texto suelto.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


# --------------------------------------------------------------------------- #
# Estados
# --------------------------------------------------------------------------- #
class EstadoEquipo(str, Enum):
    LIBRE = "LIBRE"
    OCUPADO = "OCUPADO"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"


class EstadoSesion(str, Enum):
    PROGRAMADA = "PROGRAMADA"
    EN_CURSO = "EN_CURSO"
    CERRADA = "CERRADA"
    CANCELADA = "CANCELADA"


class EstadoMaestro(str, Enum):
    SIN_ANOTAR = "SIN_ANOTAR"
    VINO = "VINO"
    NO_VINO = "NO_VINO"
    AVISO = "AVISO"


class EstadoAsistencia(str, Enum):
    PENDIENTE = "PENDIENTE"
    LLEGO = "LLEGO"
    RETARDO = "RETARDO"
    FALTA = "FALTA"


class TipoReporte(str, Enum):
    FALLA_EQUIPO = "FALLA_EQUIPO"
    OBSERVACION = "OBSERVACION"
    INCIDENTE = "INCIDENTE"


class Origen(str, Enum):
    """De dónde vino un registro de asistencia."""

    TABLETA = "TABLETA"
    MANUAL = "MANUAL"
    QR_EQUIPO = "QR_EQUIPO"


# --------------------------------------------------------------------------- #
# Personas y grupos
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Alumno:
    boleta: str
    nombre: str
    clave_grupo: str


@dataclass(frozen=True)
class Grupo:
    clave_grupo: str
    materia: str
    maestro: str


@dataclass(frozen=True)
class Laboratorio:
    id_laboratorio: str
    nombre: str


# --------------------------------------------------------------------------- #
# Clases, equipos y asistencia
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Sesion:
    """Una clase concreta: un grupo, en un laboratorio, un día y una hora."""

    id_sesion: int
    grupo: Grupo
    id_laboratorio: str
    hora_inicio: datetime
    hora_fin: datetime
    estado: EstadoSesion
    estado_maestro: EstadoMaestro


@dataclass(frozen=True)
class Equipo:
    id_equipo: int
    id_laboratorio: str
    numero: int
    estado: EstadoEquipo
    codigo: str
    alumno_actual: Optional[Alumno] = None


@dataclass(frozen=True)
class Asistencia:
    alumno: Alumno
    estado: EstadoAsistencia
    hora_llegada: Optional[datetime]
    es_retardo: bool
    numero_equipo: Optional[int]
    es_laptop: bool
    origen: Origen


@dataclass(frozen=True)
class UsoEquipo:
    id_uso: int
    id_asistencia: int
    id_equipo: int
    hora_inicio: datetime
    hora_fin: Optional[datetime]


@dataclass(frozen=True)
class Reporte:
    id_reporte: int
    tipo: TipoReporte
    id_laboratorio: str
    numero_equipo: Optional[int]
    texto: str
    fecha: datetime
    ultimo_usuario: Optional[str]


# --------------------------------------------------------------------------- #
# Resultados de archivos y estadísticas
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ErrorFila:
    numero_fila: int
    motivo: str


@dataclass(frozen=True)
class ResumenImportacion:
    agregados: int
    actualizados: int
    filas_con_error: Tuple[ErrorFila, ...] = ()

    @property
    def fue_exitosa(self) -> bool:
        return not self.filas_con_error


@dataclass(frozen=True)
class FilaEstadistica:
    materia: str
    maestros: int
    grupos: int
    grupos_que_vinieron: int
    alumnos: int


@dataclass(frozen=True)
class DiaAsistencia:
    fecha: date
    asistieron: int
    total: int


@dataclass(frozen=True)
class Periodo:
    desde: date
    hasta: date

    def __post_init__(self) -> None:
        if self.hasta < self.desde:
            raise ValueError("El periodo termina antes de empezar.")

    @classmethod
    def de_mes(cls, anio: int, mes: int) -> "Periodo":
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        return cls(date(anio, mes, 1), date(anio, mes, ultimo_dia))

    @classmethod
    def semestre(cls, referencia: Optional[date] = None) -> "Periodo":
        """Semestre que contiene a la fecha (por defecto, hoy).

        Se supone: febrero a julio y agosto a enero. Ajustar si el calendario
        escolar es otro.
        """
        referencia = referencia or date.today()
        if 2 <= referencia.month <= 7:
            return cls(date(referencia.year, 2, 1), date(referencia.year, 7, 31))
        anio_inicio = referencia.year if referencia.month >= 8 else referencia.year - 1
        return cls(date(anio_inicio, 8, 1), date(anio_inicio + 1, 1, 31))


# --------------------------------------------------------------------------- #
# Mantenimiento
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RegistroBitacora:
    fecha_hora: datetime
    accion: str
    detalle: str


@dataclass(frozen=True)
class Respaldo:
    ruta: Path
    fecha: datetime
    tamano_bytes: int


@dataclass(frozen=True)
class EstadoSistema:
    version_aplicacion: str
    version_esquema: int
    ruta_base_datos: str
    tamano_bytes: int
    total_alumnos: int
    total_clases: int
    total_respaldos: int
    ultimo_respaldo: Optional[datetime]
    problemas_integridad: Tuple[str, ...] = ()

    @property
    def integridad_ok(self) -> bool:
        return not self.problemas_integridad
