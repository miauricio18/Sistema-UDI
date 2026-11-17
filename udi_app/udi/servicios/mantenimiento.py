"""Mantenimiento: respaldos, restauración, revisión y bitácora."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .. import __version__
from ..auditoria import Auditoria
from ..base_datos import BaseDatos
from ..configuracion import Configuracion
from ..excepciones import ErrorRespaldo, RespaldoInvalido
from ..modelos import EstadoSistema, RegistroBitacora, Respaldo
from ..repositorio import RepositorioAlumnos, RepositorioBitacora, RepositorioSesiones
from ..respaldos import GestorRespaldos

LIMITE_MAXIMO_BITACORA = 5000


class ServicioMantenimiento:
    def __init__(
        self,
        base_datos: BaseDatos,
        configuracion: Configuracion,
        respaldos: GestorRespaldos,
        alumnos: RepositorioAlumnos,
        sesiones: RepositorioSesiones,
        bitacora: RepositorioBitacora,
        auditoria: Auditoria,
    ) -> None:
        self._bd = base_datos
        self._configuracion = configuracion
        self._respaldos = respaldos
        self._alumnos = alumnos
        self._sesiones = sesiones
        self._bitacora = bitacora
        self._auditoria = auditoria

    # -- respaldos ----------------------------------------------------------
    def respaldar_ahora(self) -> Respaldo:
        respaldo = self._respaldos.crear()
        if respaldo is None:
            raise ErrorRespaldo("la base de datos de ejemplo vive en memoria y no se respalda.")
        with self._bd.transaccion():
            self._auditoria.anotar("RESPALDO_MANUAL", respaldo.ruta.name)
        return respaldo

    def listar_respaldos(self) -> List[Respaldo]:
        return self._respaldos.listar()

    def limpiar_respaldos(self, conservar: int) -> int:
        """Deja solo los ``conservar`` respaldos más recientes. Devuelve cuántos borró."""
        borrados = self._respaldos.limpiar(conservar)
        with self._bd.transaccion():
            self._auditoria.anotar("LIMPIAR_RESPALDOS", f"borrados={borrados}")
        return borrados

    def restaurar_respaldo(self, ruta: Path) -> None:
        """Regresa la base al estado del respaldo. Antes guarda una copia de lo actual."""
        ruta = Path(ruta)
        if not ruta.is_file():
            raise RespaldoInvalido("no se encontró el archivo.")
        self._respaldos.crear_sin_fallar()
        self._bd.restaurar(ruta)
        with self._bd.transaccion():
            self._auditoria.anotar("RESTAURAR", ruta.name)

    # -- revisión -----------------------------------------------------------
    def verificar_integridad(self) -> List[str]:
        """Lista de problemas de la base; vacía si todo está bien."""
        return self._bd.verificar_integridad()

    def compactar(self) -> None:
        self._bd.compactar()
        with self._bd.transaccion():
            self._auditoria.anotar("COMPACTAR")

    def ver_bitacora(self, limite: int = 200) -> List[RegistroBitacora]:
        """Los cambios más recientes primero."""
        return self._bitacora.listar(max(1, min(int(limite), LIMITE_MAXIMO_BITACORA)))

    def estado_sistema(self) -> EstadoSistema:
        respaldos = self._respaldos.listar()
        return EstadoSistema(
            version_aplicacion=__version__,
            version_esquema=self._bd.version_esquema,
            ruta_base_datos=self._configuracion.ruta_bd,
            tamano_bytes=self._bd.tamano_bytes,
            total_alumnos=self._alumnos.contar(),
            total_clases=self._sesiones.contar(),
            total_respaldos=len(respaldos),
            ultimo_respaldo=respaldos[0].fecha if respaldos else None,
            problemas_integridad=tuple(self._bd.verificar_integridad()),
        )
