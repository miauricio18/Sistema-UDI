"""Log técnico del sistema (archivo ``logs/udi.log``).

El log es para quien da mantenimiento: arranques, errores con su traza,
respaldos y cada cambio de datos.
La bitácora (tabla en la base) es otra cosa: el historial de cambios de datos.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .configuracion import Configuracion

NOMBRE_LOGGER = "udi"
ARCHIVO_LOG = "udi.log"
_FORMATO = "%(asctime)s %(levelname)-8s %(message)s"
_TAMANO_MAXIMO = 1_000_000  # 1 MB por archivo
_ARCHIVOS_ANTERIORES = 5  # se conservan udi.log.1 ... udi.log.5


def configurar_registro(configuracion: Configuracion) -> logging.Logger:
    """Deja listo el logger "udi". Se puede llamar varias veces sin duplicar salidas."""
    logger = logging.getLogger(NOMBRE_LOGGER)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for anterior in list(logger.handlers):
        logger.removeHandler(anterior)
        anterior.close()

    if configuracion.en_memoria:
        logger.addHandler(logging.NullHandler())
        return logger

    configuracion.crear_carpetas()
    archivo = RotatingFileHandler(
        configuracion.carpeta_logs / ARCHIVO_LOG,
        maxBytes=_TAMANO_MAXIMO,
        backupCount=_ARCHIVOS_ANTERIORES,
        encoding="utf-8",
    )
    archivo.setFormatter(logging.Formatter(_FORMATO))
    logger.addHandler(archivo)
    return logger


def instalar_gancho_errores(logger: logging.Logger) -> None:
    """Cualquier error que nadie atrapó queda escrito en el log con su traza."""

    def gancho(tipo, valor, traza) -> None:  # type: ignore[no-untyped-def]
        if issubclass(tipo, KeyboardInterrupt):
            sys.__excepthook__(tipo, valor, traza)
            return
        logger.critical("Error no controlado", exc_info=(tipo, valor, traza))
        sys.__excepthook__(tipo, valor, traza)

    sys.excepthook = gancho
