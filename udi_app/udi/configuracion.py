"""Valores fijos del sistema y el reloj.

Todo lo que podría cambiar (tolerancia de retardo, duración de la clase,
carpetas) vive aquí y en ningún otro archivo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Configuracion:
    """Parámetros del sistema. Los valores por defecto son los de la tableta."""

    carpeta_datos: Path = field(
        default_factory=lambda: Path.home() / "Documents" / "UDI"
    )
    nombre_base_datos: str = "udi.db"
    en_memoria: bool = False

    minutos_retardo: int = 10
    minutos_clase: int = 90

    # Reservado para el registro por QR: límite de intentos por dispositivo.
    # Mientras sea None no se aplica ningún límite.
    max_intentos_por_dispositivo: Optional[int] = None

    # Límites de lo que se acepta desde fuera.
    max_megas_archivo: int = 5
    max_filas_archivo: int = 20_000
    max_caracteres_reporte: int = 500

    # Mantenimiento.
    respaldos_a_conservar: int = 60

    @classmethod
    def para_memoria(cls) -> "Configuracion":
        """Configuración para trabajar sin tocar el disco (datos de ejemplo)."""
        return cls(en_memoria=True)

    @property
    def ruta_bd(self) -> str:
        if self.en_memoria:
            return ":memory:"
        return str(self.carpeta_datos / self.nombre_base_datos)

    @property
    def carpeta_respaldos(self) -> Path:
        return self.carpeta_datos / "respaldos"

    @property
    def carpeta_exportaciones(self) -> Path:
        return self.carpeta_datos / "exportaciones"

    @property
    def carpeta_logs(self) -> Path:
        return self.carpeta_datos / "logs"

    def crear_carpetas(self) -> None:
        """Crea las carpetas de trabajo si todavía no existen."""
        if self.en_memoria:
            return
        for carpeta in (
            self.carpeta_datos,
            self.carpeta_respaldos,
            self.carpeta_exportaciones,
            self.carpeta_logs,
        ):
            carpeta.mkdir(parents=True, exist_ok=True)


class Reloj:
    """Da la hora actual. Se inyecta para no llamar a datetime.now() por todos lados."""

    def ahora(self) -> datetime:
        return datetime.now().replace(microsecond=0)
