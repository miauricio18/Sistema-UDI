"""Reportes de fallas, observaciones e incidentes, y estado de los equipos."""

from __future__ import annotations

from typing import List, Optional

from ..auditoria import Auditoria
from ..base_datos import BaseDatos
from ..configuracion import Configuracion, Reloj
from ..excepciones import DatosInvalidos, EquipoNoEncontrado, LaboratorioNoEncontrado
from ..modelos import EstadoEquipo, Reporte, TipoReporte
from ..repositorio import (
    RepositorioEquipos,
    RepositorioLaboratorios,
    RepositorioReportes,
    RepositorioUsos,
)
from ..validaciones import validar_clave, validar_enum, validar_numero_equipo, validar_texto


class ServicioReportes:
    def __init__(
        self,
        base_datos: BaseDatos,
        configuracion: Configuracion,
        reloj: Reloj,
        reportes: RepositorioReportes,
        laboratorios: RepositorioLaboratorios,
        equipos: RepositorioEquipos,
        usos: RepositorioUsos,
        auditoria: Auditoria,
    ) -> None:
        self._bd = base_datos
        self._configuracion = configuracion
        self._reloj = reloj
        self._reportes = reportes
        self._laboratorios = laboratorios
        self._equipos = equipos
        self._usos = usos
        self._auditoria = auditoria

    def crear_reporte(
        self,
        tipo: TipoReporte,
        id_laboratorio: str,
        texto: str,
        numero_equipo: Optional[int] = None,
        poner_fuera_de_servicio: bool = False,
    ) -> Reporte:
        """Guarda un reporte. Una falla puede dejar la computadora fuera de servicio."""
        tipo = validar_enum(tipo, TipoReporte, "El tipo de reporte")
        id_laboratorio = validar_clave(id_laboratorio, "El laboratorio")
        texto = validar_texto(
            texto, "qué pasó", maximo=self._configuracion.max_caracteres_reporte
        )
        if numero_equipo is not None:
            numero_equipo = validar_numero_equipo(numero_equipo)
        if self._laboratorios.buscar(id_laboratorio) is None:
            raise LaboratorioNoEncontrado(id_laboratorio)
        if tipo is TipoReporte.FALLA_EQUIPO and numero_equipo is None:
            raise DatosInvalidos("Indica la computadora que falló.")
        if poner_fuera_de_servicio and numero_equipo is None:
            raise DatosInvalidos("Indica qué computadora se pone fuera de servicio.")

        equipo = None
        if numero_equipo is not None:
            equipo = self._equipos.buscar(id_laboratorio, numero_equipo)
            if equipo is None:
                raise EquipoNoEncontrado(id_laboratorio, numero_equipo)

        ahora = self._reloj.ahora()
        with self._bd.transaccion():
            reporte = self._reportes.guardar(
                tipo=tipo,
                id_laboratorio=id_laboratorio,
                id_equipo=equipo.id_equipo if equipo else None,
                texto=texto,
                fecha=ahora,
                ultimo_usuario=self._usos.ultimo_usuario(equipo.id_equipo) if equipo else None,
            )
            if equipo is not None and poner_fuera_de_servicio:
                self._equipos.cambiar_estado(equipo.id_equipo, EstadoEquipo.FUERA_DE_SERVICIO)
                # Quien la estaba usando en clases no cerradas queda sin equipo.
                self._usos.cerrar_abiertos_de_equipo(equipo.id_equipo, ahora)
            self._auditoria.anotar(
                "REPORTE",
                f"id={reporte.id_reporte} tipo={tipo.value} lab={id_laboratorio} "
                f"equipo={numero_equipo} fuera_de_servicio={poner_fuera_de_servicio}",
            )
        return reporte

    def reactivar_equipo(self, id_laboratorio: str, numero_equipo: int) -> None:
        """Devuelve una computadora a servicio."""
        numero_equipo = validar_numero_equipo(numero_equipo)
        equipo = self._equipos.buscar(id_laboratorio, numero_equipo)
        if equipo is None:
            raise EquipoNoEncontrado(id_laboratorio, numero_equipo)
        with self._bd.transaccion():
            self._equipos.cambiar_estado(equipo.id_equipo, EstadoEquipo.LIBRE)
            self._auditoria.anotar(
                "REACTIVAR_EQUIPO", f"lab={id_laboratorio} equipo={numero_equipo}"
            )

    def listar_reportes(self) -> List[Reporte]:
        """Del más reciente al más antiguo."""
        return self._reportes.listar()
