"""Deja constancia de cada cambio: en la bitácora (base de datos) y en el log."""

from __future__ import annotations

import logging

from .configuracion import Reloj
from .repositorio import RepositorioBitacora


class Auditoria:
    """Los servicios la usan para anotar qué se hizo y cuándo."""

    def __init__(
        self, bitacora: RepositorioBitacora, reloj: Reloj, logger: logging.Logger
    ) -> None:
        self._bitacora = bitacora
        self._reloj = reloj
        self._logger = logger

    def anotar(self, accion: str, detalle: str = "") -> None:
        self._bitacora.anotar(self._reloj.ahora(), accion, detalle)
        self._logger.info("%s %s", accion, detalle)
