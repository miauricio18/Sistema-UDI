"""Horario de clases: crear, cambiar y cancelar sesiones."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from ..auditoria import Auditoria
from ..base_datos import BaseDatos
from ..configuracion import Configuracion, Reloj
from ..excepciones import (
    DatosInvalidos,
    GrupoNoEncontrado,
    HorarioEmpalmado,
    LaboratorioNoEncontrado,
    SesionNoEncontrada,
)
from ..modelos import EstadoSesion, Grupo, Laboratorio, Sesion
from ..repositorio import (
    RepositorioGrupos,
    RepositorioLaboratorios,
    RepositorioSesiones,
)


class ServicioHorario:
    """Una clase cancelada no se borra: queda con estado CANCELADA."""

    def __init__(
        self,
        base_datos: BaseDatos,
        configuracion: Configuracion,
        reloj: Reloj,
        sesiones: RepositorioSesiones,
        grupos: RepositorioGrupos,
        laboratorios: RepositorioLaboratorios,
        auditoria: Auditoria,
    ) -> None:
        self._bd = base_datos
        self._configuracion = configuracion
        self._reloj = reloj
        self._sesiones = sesiones
        self._grupos = grupos
        self._laboratorios = laboratorios
        self._auditoria = auditoria

    # -- consultas ------------------------------------------------------------
    def listar_dia(self, dia: Optional[date] = None) -> List[Sesion]:
        return self._sesiones.listar_del_dia(dia or self._reloj.ahora().date())

    def listar_grupos(self) -> List[Grupo]:
        return self._grupos.listar()

    def listar_laboratorios(self) -> List[Laboratorio]:
        return self._laboratorios.listar()

    # -- cambios --------------------------------------------------------------
    def crear_clase(
        self,
        clave_grupo: str,
        id_laboratorio: str,
        hora_inicio: datetime,
        hora_fin: Optional[datetime] = None,
    ) -> Sesion:
        hora_fin = self._hora_fin(hora_inicio, hora_fin)
        self._validar(clave_grupo, id_laboratorio, hora_inicio, hora_fin)
        with self._bd.transaccion():
            id_sesion = self._sesiones.crear(clave_grupo, id_laboratorio, hora_inicio, hora_fin)
            self._anotar("CREAR_CLASE", f"sesion={id_sesion} grupo={clave_grupo} lab={id_laboratorio}")
        return self._sesiones.buscar(id_sesion)

    def editar_clase(
        self,
        id_sesion: int,
        clave_grupo: str,
        id_laboratorio: str,
        hora_inicio: datetime,
        hora_fin: Optional[datetime] = None,
    ) -> Sesion:
        self._exigir_modificable(id_sesion)
        hora_fin = self._hora_fin(hora_inicio, hora_fin)
        self._validar(clave_grupo, id_laboratorio, hora_inicio, hora_fin, ignorar=id_sesion)
        with self._bd.transaccion():
            self._sesiones.actualizar_clase(
                id_sesion, clave_grupo, id_laboratorio, hora_inicio, hora_fin
            )
            self._anotar("EDITAR_CLASE", f"sesion={id_sesion} grupo={clave_grupo} lab={id_laboratorio}")
        return self._sesiones.buscar(id_sesion)

    def cancelar_clase(self, id_sesion: int) -> None:
        self._exigir_modificable(id_sesion)
        with self._bd.transaccion():
            self._sesiones.cambiar_estado(id_sesion, EstadoSesion.CANCELADA)
            self._anotar("CANCELAR_CLASE", f"sesion={id_sesion}")

    # -- apoyo interno --------------------------------------------------------
    def _hora_fin(self, inicio: datetime, fin: Optional[datetime]) -> datetime:
        if not isinstance(inicio, datetime) or not isinstance(fin, (datetime, type(None))):
            raise DatosInvalidos("La fecha y la hora de la clase no son válidas.")
        return fin or inicio + timedelta(minutes=self._configuracion.minutos_clase)

    def _exigir_modificable(self, id_sesion: int) -> Sesion:
        sesion = self._sesiones.buscar(id_sesion)
        if sesion is None or sesion.estado is EstadoSesion.CANCELADA:
            raise SesionNoEncontrada()
        if sesion.estado is EstadoSesion.CERRADA:
            raise DatosInvalidos("La clase ya se cerró y no se puede modificar.")
        return sesion

    def _validar(
        self,
        clave_grupo: str,
        id_laboratorio: str,
        hora_inicio: datetime,
        hora_fin: datetime,
        ignorar: Optional[int] = None,
    ) -> None:
        if hora_fin <= hora_inicio:
            raise DatosInvalidos("La clase debe terminar después de empezar.")
        if self._grupos.buscar(clave_grupo) is None:
            raise GrupoNoEncontrado(clave_grupo)
        if self._laboratorios.buscar(id_laboratorio) is None:
            raise LaboratorioNoEncontrado(id_laboratorio)
        choque = self._sesiones.buscar_empalme(id_laboratorio, hora_inicio, hora_fin, ignorar)
        if choque is not None:
            raise HorarioEmpalmado(
                id_laboratorio, f"{choque.grupo.materia} ({choque.grupo.clave_grupo})"
            )

    def _anotar(self, accion: str, detalle: str) -> None:
        self._auditoria.anotar(accion, detalle)
