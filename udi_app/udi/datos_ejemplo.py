"""Datos ficticios para probar la interfaz sin archivos reales.

Todos los nombres, boletas y grupos son inventados.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple

from .base_datos import BaseDatos
from .modelos import Alumno, EstadoEquipo, Grupo, Laboratorio
from .repositorio import (
    RepositorioAlumnos,
    RepositorioEquipos,
    RepositorioGrupos,
    RepositorioLaboratorios,
    RepositorioSesiones,
)

EQUIPOS_POR_LABORATORIO = 40

_GRUPOS: List[Grupo] = [
    Grupo("3CM1", "Programación Orientada a Objetos", "Dra. Ana Torres"),
    Grupo("3CM2", "Bases de Datos", "Mtro. Luis Herrera"),
    Grupo("5CV1", "Redes de Computadoras", "Mtra. Rosa Medina"),
]

_NOMBRES = [
    "Sofía", "Mateo", "Valeria", "Diego", "Camila", "Santiago",
    "Daniela", "Emilio", "Regina", "Leonardo", "Ximena", "Iker",
]
_APELLIDOS = [
    "García", "Hernández", "López", "Martínez", "Rodríguez", "Pérez",
    "Sánchez", "Ramírez", "Flores", "Cruz", "Morales", "Reyes",
]


def _alumnos_de(grupo: Grupo, indice_grupo: int) -> List[Alumno]:
    alumnos = []
    for i, nombre in enumerate(_NOMBRES):
        apellido = _APELLIDOS[(i + indice_grupo * 3) % len(_APELLIDOS)]
        boleta = f"2026{indice_grupo + 1:02d}{i + 1:04d}"
        alumnos.append(Alumno(boleta, f"{nombre} {apellido}", grupo.clave_grupo))
    return alumnos


def cargar_datos_ejemplo(base_datos: BaseDatos, ahora: datetime, minutos_clase: int = 90) -> None:
    """Llena la base con grupos, alumnos, laboratorios, equipos y clases de hoy.

    La primera clase empieza 5 minutos antes de ``ahora``, así siempre hay una
    clase "en curso" al abrir la interfaz.
    """
    grupos = RepositorioGrupos(base_datos)
    alumnos = RepositorioAlumnos(base_datos)
    laboratorios = RepositorioLaboratorios(base_datos)
    equipos = RepositorioEquipos(base_datos)
    sesiones = RepositorioSesiones(base_datos)

    with base_datos.transaccion():
        for indice, grupo in enumerate(_GRUPOS):
            grupos.guardar(grupo)
            for alumno in _alumnos_de(grupo, indice):
                alumnos.guardar(alumno)
                alumnos.inscribir(alumno.boleta, grupo.clave_grupo)

        for id_lab, nombre in (("L1", "UDI 1"), ("L2", "UDI 2")):
            laboratorios.guardar(Laboratorio(id_lab, nombre))
            for numero in range(1, EQUIPOS_POR_LABORATORIO + 1):
                equipos.crear(id_lab, numero, f"{id_lab}-{numero}")

        fuera = equipos.buscar("L1", EQUIPOS_POR_LABORATORIO)
        if fuera is not None:
            equipos.cambiar_estado(fuera.id_equipo, EstadoEquipo.FUERA_DE_SERVICIO)

        duracion = timedelta(minutes=minutos_clase)
        inicio = ahora.replace(microsecond=0) - timedelta(minutes=5)
        clases: List[Tuple[str, str, datetime]] = [
            ("3CM1", "L1", inicio),
            ("3CM2", "L2", inicio + timedelta(minutes=30)),
            ("5CV1", "L1", inicio + duracion + timedelta(minutes=10)),
        ]
        for clave, id_lab, hora in clases:
            sesiones.crear(clave, id_lab, hora, hora + duracion)
