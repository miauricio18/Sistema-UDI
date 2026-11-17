"""Alta de laboratorios y de sus computadoras (configuración inicial)."""

from __future__ import annotations

from typing import List

from ..auditoria import Auditoria
from ..base_datos import BaseDatos
from ..modelos import Laboratorio
from ..repositorio import RepositorioEquipos, RepositorioLaboratorios
from ..validaciones import validar_clave, validar_numero_equipo, validar_texto

LARGO_MAXIMO_NOMBRE_LABORATORIO = 60


class ServicioLaboratorios:
    def __init__(
        self,
        base_datos: BaseDatos,
        laboratorios: RepositorioLaboratorios,
        equipos: RepositorioEquipos,
        auditoria: Auditoria,
    ) -> None:
        self._bd = base_datos
        self._laboratorios = laboratorios
        self._equipos = equipos
        self._auditoria = auditoria

    def listar(self) -> List[Laboratorio]:
        return self._laboratorios.listar()

    def registrar_laboratorio(
        self, id_laboratorio: str, nombre: str, total_equipos: int
    ) -> Laboratorio:
        """Crea el laboratorio (o le cambia el nombre) y sus computadoras 1..total.

        Cada computadora recibe su código único, por ejemplo L1-17. Se puede
        volver a llamar con un total mayor para agregar computadoras; las que ya
        existen no se tocan y nunca se borran.
        """
        id_laboratorio = validar_clave(id_laboratorio, "La clave del laboratorio")
        nombre = validar_texto(
            nombre, "el nombre del laboratorio", maximo=LARGO_MAXIMO_NOMBRE_LABORATORIO
        )
        total_equipos = validar_numero_equipo(total_equipos)
        laboratorio = Laboratorio(id_laboratorio, nombre)
        with self._bd.transaccion():
            self._laboratorios.guardar(laboratorio)
            for numero in range(1, total_equipos + 1):
                self._equipos.crear(id_laboratorio, numero, f"{id_laboratorio}-{numero}")
            self._auditoria.anotar(
                "REGISTRAR_LABORATORIO", f"lab={id_laboratorio} equipos={total_equipos}"
            )
        return laboratorio
