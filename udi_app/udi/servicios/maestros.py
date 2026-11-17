"""Registro de si el maestro vino a su clase."""

from __future__ import annotations

from ..auditoria import Auditoria
from ..base_datos import BaseDatos
from ..excepciones import SesionNoEncontrada
from ..modelos import EstadoMaestro, EstadoSesion, Sesion
from ..repositorio import RepositorioSesiones
from ..validaciones import validar_enum


class ServicioMaestros:
    """Vino / No vino / Avisó. Avisó cuenta como clase cumplida."""

    def __init__(
        self,
        base_datos: BaseDatos,
        sesiones: RepositorioSesiones,
        auditoria: Auditoria,
    ) -> None:
        self._bd = base_datos
        self._sesiones = sesiones
        self._auditoria = auditoria

    def marcar_maestro(self, id_sesion: int, estado: EstadoMaestro) -> Sesion:
        estado = validar_enum(estado, EstadoMaestro, "El estado del maestro")
        sesion = self._sesiones.buscar(id_sesion)
        if sesion is None or sesion.estado is EstadoSesion.CANCELADA:
            raise SesionNoEncontrada()
        with self._bd.transaccion():
            self._sesiones.cambiar_estado_maestro(id_sesion, estado)
            self._auditoria.anotar("MAESTRO", f"sesion={id_sesion} estado={estado.value}")
        return self._sesiones.buscar(id_sesion)

    @staticmethod
    def cumplio(estado: EstadoMaestro) -> bool:
        """True si la clase se considera cumplida (vino o avisó)."""
        return estado in (EstadoMaestro.VINO, EstadoMaestro.AVISO)
