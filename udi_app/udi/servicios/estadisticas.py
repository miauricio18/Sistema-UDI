"""Estadísticas de asistencia por materia y por grupo."""

from __future__ import annotations

from typing import List

from ..modelos import DiaAsistencia, FilaEstadistica, Periodo
from ..repositorio import RepositorioAsistencias
from ..validaciones import validar_clave


class ServicioEstadisticas:
    """Solo lee. Definiciones usadas:

    * ``grupos_que_vinieron``: grupos de la materia con al menos un alumno que llegó
      (a tiempo o con retardo) en el periodo.
    * ``alumnos``: alumnos distintos que llegaron en el periodo (no se cuentan dos veces).
    """

    def __init__(self, asistencias: RepositorioAsistencias) -> None:
        self._asistencias = asistencias

    def resumen_por_materia(self, periodo: Periodo) -> List[FilaEstadistica]:
        return self._asistencias.resumen_por_materia(periodo)

    def asistencia_por_dia(self, clave_grupo: str, periodo: Periodo) -> List[DiaAsistencia]:
        clave_grupo = validar_clave(clave_grupo, "El grupo")
        return self._asistencias.conteo_por_dia(clave_grupo, periodo)
