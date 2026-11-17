"""Copias de seguridad de la base: crear, listar y borrar las más viejas."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .base_datos import BaseDatos
from .configuracion import Configuracion, Reloj
from .excepciones import ErrorUDI
from .modelos import Respaldo

PATRON_ARCHIVOS = "udi_*.db"
_FORMATO_FECHA = "udi_%Y%m%d_%H%M%S"


class GestorRespaldos:
    def __init__(
        self,
        base_datos: BaseDatos,
        configuracion: Configuracion,
        reloj: Reloj,
        logger: logging.Logger,
    ) -> None:
        self._bd = base_datos
        self._configuracion = configuracion
        self._reloj = reloj
        self._logger = logger

    def crear(self) -> Optional[Respaldo]:
        """Hace una copia y borra las que sobran. None si la base está en memoria."""
        ruta = self._bd.respaldar(self._reloj.ahora())
        if ruta is None:
            return None
        self._logger.info("RESPALDO creado %s", ruta.name)
        self.limpiar()
        return self._describir(ruta)

    def crear_sin_fallar(self) -> Optional[Respaldo]:
        """Para respaldos automáticos: si falla se anota en el log y se sigue."""
        try:
            return self.crear()
        except (ErrorUDI, OSError):
            self._logger.exception("No se pudo crear el respaldo automático")
            return None

    def listar(self) -> List[Respaldo]:
        """Del más reciente al más antiguo."""
        if self._configuracion.en_memoria:
            return []
        carpeta = self._configuracion.carpeta_respaldos
        respaldos = [self._describir(ruta) for ruta in carpeta.glob(PATRON_ARCHIVOS)]
        return sorted(respaldos, key=lambda r: (r.fecha, r.ruta.name), reverse=True)

    def limpiar(self, conservar: Optional[int] = None) -> int:
        """Borra los respaldos más viejos. Devuelve cuántos borró."""
        limite = self._configuracion.respaldos_a_conservar if conservar is None else conservar
        sobrantes = self.listar()[max(limite, 1):]  # nunca se borra el más reciente
        for respaldo in sobrantes:
            respaldo.ruta.unlink(missing_ok=True)
        if sobrantes:
            self._logger.info("RESPALDOS borrados %d antiguos", len(sobrantes))
        return len(sobrantes)

    @staticmethod
    def _describir(ruta: Path) -> Respaldo:
        datos = ruta.stat()
        try:
            # El nombre puede traer un sufijo (_1) si hubo dos en el mismo segundo.
            fecha = datetime.strptime(ruta.stem[:19], _FORMATO_FECHA)
        except ValueError:
            fecha = datetime.fromtimestamp(datos.st_mtime).replace(microsecond=0)
        return Respaldo(ruta=ruta, fecha=fecha, tamano_bytes=datos.st_size)
