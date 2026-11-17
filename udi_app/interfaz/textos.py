"""Cómo se escribe cada dato en pantalla, y cómo se lee lo que escribe la persona.

Son funciones puras (no usan Tkinter), así que se prueban sin abrir ventanas.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Dict, Optional

from udi.excepciones import DatosInvalidos
from udi.modelos import (
    EstadoAsistencia,
    EstadoEquipo,
    EstadoMaestro,
    EstadoSesion,
    Sesion,
    TipoReporte,
)

ASISTENCIA: Dict[EstadoAsistencia, str] = {
    EstadoAsistencia.PENDIENTE: "Pendiente",
    EstadoAsistencia.LLEGO: "A tiempo",
    EstadoAsistencia.RETARDO: "Retardo",
    EstadoAsistencia.FALTA: "Falta",
}

SESION: Dict[EstadoSesion, str] = {
    EstadoSesion.PROGRAMADA: "Programada",
    EstadoSesion.EN_CURSO: "En curso",
    EstadoSesion.CERRADA: "Cerrada",
    EstadoSesion.CANCELADA: "Cancelada",
}

MAESTRO: Dict[EstadoMaestro, str] = {
    EstadoMaestro.SIN_ANOTAR: "Sin anotar",
    EstadoMaestro.VINO: "Vino",
    EstadoMaestro.NO_VINO: "No vino",
    EstadoMaestro.AVISO: "Avisó",
}

REPORTE: Dict[TipoReporte, str] = {
    TipoReporte.FALLA_EQUIPO: "Falla de equipo",
    TipoReporte.OBSERVACION: "Observación",
    TipoReporte.INCIDENTE: "Incidente",
}

EQUIPO: Dict[EstadoEquipo, str] = {
    EstadoEquipo.LIBRE: "Libre",
    EstadoEquipo.OCUPADO: "Ocupada",
    EstadoEquipo.FUERA_DE_SERVICIO: "Fuera de servicio",
}

_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
_FORMATOS_FECHA = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d")
_FORMATOS_HORA = ("%H:%M", "%H.%M", "%H%M")


# --------------------------------------------------------------------------- #
# Del sistema a la pantalla
# --------------------------------------------------------------------------- #
def hora(momento: Optional[datetime]) -> str:
    return momento.strftime("%H:%M") if momento else ""


def fecha_corta(dia: date) -> str:
    return dia.strftime("%d/%m/%Y")


def fecha_larga(dia: date) -> str:
    """Por ejemplo: «Lunes 16 de noviembre de 2026». No depende del idioma de Windows."""
    texto = f"{_DIAS[dia.weekday()]} {dia.day} de {_MESES[dia.month - 1]} de {dia.year}"
    return texto[0].upper() + texto[1:]


def fecha_hora(momento: Optional[datetime]) -> str:
    return momento.strftime("%d/%m/%Y %H:%M") if momento else "—"


def nombre_mes(dia: date) -> str:
    return f"{_MESES[dia.month - 1].capitalize()} {dia.year}"


def horario_clase(sesion: Sesion) -> str:
    return f"{hora(sesion.hora_inicio)}–{hora(sesion.hora_fin)}"


def resumen_clase(sesion: Sesion) -> str:
    """Una línea para elegir la clase en una lista desplegable."""
    grupo = sesion.grupo
    return (
        f"{hora(sesion.hora_inicio)} · {grupo.materia} ({grupo.clave_grupo}) "
        f"· {sesion.id_laboratorio}"
    )


def nombre_corto(nombre: str, largo: int = 8) -> str:
    """Primer nombre, recortado para que quepa en un cuadro del mapa."""
    primero = nombre.split()[0] if nombre.split() else ""
    return primero if len(primero) <= largo else primero[: largo - 1] + "…"


def tamano(en_bytes: int) -> str:
    if en_bytes < 1024 * 1024:
        return f"{max(1, round(en_bytes / 1024))} KB"
    return f"{en_bytes / (1024 * 1024):.1f} MB"


def porcentaje(parte: int, total: int) -> str:
    return f"{round(100 * parte / total)} %" if total else "—"


# --------------------------------------------------------------------------- #
# De la pantalla al sistema
# --------------------------------------------------------------------------- #
def leer_fecha(texto: str) -> date:
    limpio = (texto or "").strip()
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(limpio, formato).date()
        except ValueError:
            continue
    raise DatosInvalidos("Escribe la fecha como día/mes/año, por ejemplo 16/11/2026.")


def leer_hora(texto: str) -> time:
    limpio = (texto or "").strip()
    for formato in _FORMATOS_HORA:
        try:
            return datetime.strptime(limpio, formato).time()
        except ValueError:
            continue
    raise DatosInvalidos("Escribe la hora con 24 horas, por ejemplo 07:00 o 13:30.")


def leer_entero(texto: str, campo: str) -> int:
    limpio = (texto or "").strip()
    if not limpio.isdigit():
        raise DatosInvalidos(f"{campo} debe ser un número.")
    return int(limpio)
