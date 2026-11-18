"""Pase de lista y uso de equipos de una clase.

Es el servicio que más usa la encargada: registrar llegadas, asignar
computadora, anotar laptop propia y cerrar o reabrir el pase de lista.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import List, Optional

from ..auditoria import Auditoria
from ..base_datos import BaseDatos
from ..configuracion import Configuracion, Reloj
from ..excepciones import (
    AlumnoNoEncontrado,
    EquipoFueraDeServicio,
    EquipoNoEncontrado,
    EquipoOcupado,
    GrupoDistinto,
    PaseListaCerrado,
    SesionNoEncontrada,
)
from ..modelos import (
    Asistencia,
    EstadoAsistencia,
    EstadoEquipo,
    EstadoSesion,
    Equipo,
    Origen,
    Sesion,
)
from ..repositorio import (
    RepositorioAlumnos,
    RepositorioAsistencias,
    RepositorioEquipos,
    RepositorioSesiones,
    RepositorioUsos,
)
from ..respaldos import GestorRespaldos
from ..utilidades import a_texto_boleta
from ..validaciones import es_boleta_valida, validar_enum, validar_numero_equipo

_CON_LLEGADA = (EstadoAsistencia.LLEGO, EstadoAsistencia.RETARDO)


class ServicioAsistencia:
    """Reglas del pase de lista. No sabe de pantallas ni de SQL."""

    def __init__(
        self,
        base_datos: BaseDatos,
        configuracion: Configuracion,
        reloj: Reloj,
        alumnos: RepositorioAlumnos,
        sesiones: RepositorioSesiones,
        equipos: RepositorioEquipos,
        asistencias: RepositorioAsistencias,
        usos: RepositorioUsos,
        respaldos: GestorRespaldos,
        auditoria: Auditoria,
    ) -> None:
        self._bd = base_datos
        self._configuracion = configuracion
        self._reloj = reloj
        self._alumnos = alumnos
        self._sesiones = sesiones
        self._equipos = equipos
        self._asistencias = asistencias
        self._usos = usos
        self._respaldos = respaldos
        self._auditoria = auditoria

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def obtener_sesion_actual(self) -> Sesion:
        """Clase en curso; si no hay, la siguiente del día; si no, error."""
        ahora = self._reloj.ahora()
        abiertas = [
            s
            for s in self._sesiones.listar_del_dia(ahora.date())
            if s.estado is not EstadoSesion.CERRADA
        ]
        en_curso = [
            s
            for s in abiertas
            if s.estado is EstadoSesion.EN_CURSO or s.hora_inicio <= ahora < s.hora_fin
        ]
        if en_curso:
            return en_curso[0]
        proximas = [s for s in abiertas if s.hora_inicio > ahora]
        if proximas:
            return proximas[0]
        raise SesionNoEncontrada()

    def obtener_lista(self, id_sesion: int) -> List[Asistencia]:
        """Todos los alumnos del grupo; quien no ha llegado aparece PENDIENTE."""
        sesion = self._obtener_sesion(id_sesion)
        registradas = {
            a.alumno.boleta: a for a in self._asistencias.listar_por_sesion(id_sesion)
        }
        lista: List[Asistencia] = []
        for alumno in self._alumnos.listar_por_grupo(sesion.grupo.clave_grupo):
            lista.append(registradas.pop(alumno.boleta, None) or self._pendiente(alumno))
        # Asistencias de alguien que ya no está inscrito: se conservan al final.
        lista.extend(registradas.values())
        return lista

    def mapa_laboratorio(self, id_sesion: int) -> List[Equipo]:
        """Equipos del laboratorio con su estado en esta clase.

        OCUPADO se calcula aquí: depende de la clase, no se guarda.
        """
        sesion = self._obtener_sesion(id_sesion)
        ocupantes = self._usos.ocupantes_de_sesion(id_sesion)
        mapa: List[Equipo] = []
        for equipo in self._equipos.listar_laboratorio(sesion.id_laboratorio):
            ocupante = ocupantes.get(equipo.id_equipo)
            if equipo.estado is EstadoEquipo.FUERA_DE_SERVICIO:
                mapa.append(equipo)
            elif ocupante is not None:
                mapa.append(replace(equipo, estado=EstadoEquipo.OCUPADO, alumno_actual=ocupante))
            else:
                mapa.append(equipo)
        return mapa

    # ------------------------------------------------------------------ #
    # Registro
    # ------------------------------------------------------------------ #
    def registrar_llegada(
        self, id_sesion: int, boleta: str, origen: Origen = Origen.TABLETA
    ) -> Asistencia:
        sesion = self._obtener_sesion(id_sesion)
        self._exigir_pase_abierto(sesion)
        with self._bd.transaccion():
            return self._registrar(sesion, boleta, origen)

    def asignar_equipo(
        self,
        id_sesion: int,
        boleta: str,
        numero_equipo: int,
        origen: Origen = Origen.TABLETA,
    ) -> Asistencia:
        """Asigna computadora. Si el alumno no había llegado, registra su llegada."""
        sesion = self._obtener_sesion(id_sesion)
        self._exigir_pase_abierto(sesion)
        with self._bd.transaccion():
            asistencia = self._registrar(sesion, boleta, origen)
            numero_equipo = validar_numero_equipo(numero_equipo)
            equipo = self._equipos.buscar(sesion.id_laboratorio, numero_equipo)
            if equipo is None:
                raise EquipoNoEncontrado(sesion.id_laboratorio, numero_equipo)
            if equipo.estado is EstadoEquipo.FUERA_DE_SERVICIO:
                raise EquipoFueraDeServicio(numero_equipo)

            ocupante = self._usos.ocupante(id_sesion, equipo.id_equipo)
            if ocupante is not None:
                if ocupante.boleta == asistencia.alumno.boleta:
                    return asistencia
                raise EquipoOcupado(numero_equipo, ocupante.nombre)

            ahora = self._reloj.ahora()
            id_asistencia = self._id_asistencia(id_sesion, asistencia.alumno.boleta)
            self._usos.cerrar_de_asistencia(id_asistencia, ahora)  # suelta la anterior
            self._usos.abrir(id_asistencia, equipo.id_equipo, ahora)
            self._anotar(
                "ASIGNAR_EQUIPO",
                f"sesion={id_sesion} boleta={asistencia.alumno.boleta} equipo={numero_equipo}",
            )
            return self._leer(id_sesion, asistencia.alumno.boleta)

    def liberar_equipo(self, id_sesion: int, boleta: str) -> Asistencia:
        """Quita la computadora al alumno sin cambiar su asistencia."""
        sesion = self._obtener_sesion(id_sesion)
        self._exigir_pase_abierto(sesion)
        boleta = a_texto_boleta(boleta)
        with self._bd.transaccion():
            asistencia = self._asistencias.buscar(id_sesion, boleta)
            if asistencia is None:
                raise AlumnoNoEncontrado()
            id_asistencia = self._id_asistencia(id_sesion, boleta)
            self._usos.cerrar_de_asistencia(id_asistencia, self._reloj.ahora())
            self._anotar("LIBERAR_EQUIPO", f"sesion={id_sesion} boleta={boleta}")
            return self._leer(id_sesion, boleta)

    def marcar_laptop(self, id_sesion: int, boleta: str, es_laptop: bool = True) -> Asistencia:
        """Anota que el alumno trabaja con su laptop propia.

        Es solo una nota: el alumno se sienta igual en un lugar del laboratorio,
        así que conserva (o recibe después) su computadora en el mapa.
        """
        sesion = self._obtener_sesion(id_sesion)
        self._exigir_pase_abierto(sesion)
        with self._bd.transaccion():
            asistencia = self._registrar(sesion, boleta, Origen.TABLETA)
            id_asistencia = self._id_asistencia(id_sesion, asistencia.alumno.boleta)
            self._asistencias.marcar_laptop(id_asistencia, es_laptop)
            self._anotar(
                "LAPTOP",
                f"sesion={id_sesion} boleta={asistencia.alumno.boleta} laptop={es_laptop}",
            )
            return self._leer(id_sesion, asistencia.alumno.boleta)

    # ------------------------------------------------------------------ #
    # Cierre del pase de lista
    # ------------------------------------------------------------------ #
    def terminar_pase_lista(self, id_sesion: int) -> List[Asistencia]:
        """Quien no llegó queda con FALTA, la clase se cierra y se hace respaldo."""
        sesion = self._obtener_sesion(id_sesion)
        if sesion.estado is not EstadoSesion.CERRADA:
            with self._bd.transaccion():
                registradas = {
                    a.alumno.boleta for a in self._asistencias.listar_por_sesion(id_sesion)
                }
                for alumno in self._alumnos.listar_por_grupo(sesion.grupo.clave_grupo):
                    if alumno.boleta not in registradas:
                        self._asistencias.guardar(
                            id_sesion,
                            Asistencia(
                                alumno=alumno,
                                estado=EstadoAsistencia.FALTA,
                                hora_llegada=None,
                                es_retardo=False,
                                numero_equipo=None,
                                es_laptop=False,
                                origen=Origen.TABLETA,
                            ),
                        )
                self._sesiones.cambiar_estado(id_sesion, EstadoSesion.CERRADA)
                self._anotar("TERMINAR_PASE", f"sesion={id_sesion}")
            self._respaldos.crear_sin_fallar()
        return self._asistencias.listar_por_sesion(id_sesion)

    def reabrir_pase_lista(self, id_sesion: int) -> Sesion:
        """La clase vuelve a EN_CURSO y las faltas vuelven a ser pendientes."""
        sesion = self._obtener_sesion(id_sesion)
        if sesion.estado is EstadoSesion.CERRADA:
            with self._bd.transaccion():
                self._asistencias.eliminar_faltas(id_sesion)
                self._sesiones.cambiar_estado(id_sesion, EstadoSesion.EN_CURSO)
                self._anotar("REABRIR_PASE", f"sesion={id_sesion}")
        return self._obtener_sesion(id_sesion)

    # ------------------------------------------------------------------ #
    # Apoyo interno
    # ------------------------------------------------------------------ #
    def _obtener_sesion(self, id_sesion: int) -> Sesion:
        sesion = self._sesiones.buscar(id_sesion)
        if sesion is None or sesion.estado is EstadoSesion.CANCELADA:
            raise SesionNoEncontrada()
        return sesion

    @staticmethod
    def _exigir_pase_abierto(sesion: Sesion) -> None:
        if sesion.estado is EstadoSesion.CERRADA:
            raise PaseListaCerrado()

    def _registrar(self, sesion: Sesion, boleta: str, origen: Origen) -> Asistencia:
        """Registra la llegada (si falta) respetando el orden de validaciones."""
        boleta = a_texto_boleta(boleta)
        origen = validar_enum(origen, Origen, "El origen")
        if not es_boleta_valida(boleta):  # ni siquiera se consulta la base
            raise AlumnoNoEncontrado()
        alumno = self._alumnos.buscar(boleta)
        if alumno is None:
            raise AlumnoNoEncontrado()
        if not self._alumnos.esta_inscrito(boleta, sesion.grupo.clave_grupo):
            raise GrupoDistinto(alumno.nombre, self._clase_de_hoy(boleta, sesion))

        existente = self._asistencias.buscar(sesion.id_sesion, boleta)
        if existente is not None and existente.estado in _CON_LLEGADA:
            return existente

        ahora = self._reloj.ahora()
        limite = sesion.hora_inicio + timedelta(minutes=self._configuracion.minutos_retardo)
        es_retardo = ahora > limite
        self._asistencias.guardar(
            sesion.id_sesion,
            Asistencia(
                alumno=alumno,
                estado=EstadoAsistencia.RETARDO if es_retardo else EstadoAsistencia.LLEGO,
                hora_llegada=ahora,
                es_retardo=es_retardo,
                numero_equipo=None,
                es_laptop=False,
                origen=origen,
            ),
        )
        if sesion.estado is EstadoSesion.PROGRAMADA:
            self._sesiones.cambiar_estado(sesion.id_sesion, EstadoSesion.EN_CURSO)
        self._anotar(
            "LLEGADA",
            f"sesion={sesion.id_sesion} boleta={boleta} retardo={es_retardo} origen={origen.value}",
        )
        return self._leer(sesion.id_sesion, boleta)

    def _clase_de_hoy(self, boleta: str, sesion: Sesion) -> Optional[str]:
        """Descripción de la clase que el alumno sí tiene ese día, si la hay."""
        grupos = set(self._alumnos.grupos_de(boleta))
        del_dia = self._sesiones.listar_del_dia(sesion.hora_inicio.date())
        suyas = [s for s in del_dia if s.grupo.clave_grupo in grupos]
        if not suyas:
            return None
        pendientes = [s for s in suyas if s.estado is not EstadoSesion.CERRADA]
        elegida = (pendientes or suyas)[0]
        return (
            f"{elegida.grupo.materia} ({elegida.grupo.clave_grupo}) "
            f"a las {elegida.hora_inicio:%H:%M} en {elegida.id_laboratorio}"
        )

    def _id_asistencia(self, id_sesion: int, boleta: str) -> int:
        id_asistencia = self._asistencias.id_de(id_sesion, boleta)
        if id_asistencia is None:
            raise AlumnoNoEncontrado()
        return id_asistencia

    def _leer(self, id_sesion: int, boleta: str) -> Asistencia:
        asistencia = self._asistencias.buscar(id_sesion, boleta)
        if asistencia is None:
            raise AlumnoNoEncontrado()
        return asistencia

    @staticmethod
    def _pendiente(alumno) -> Asistencia:
        return Asistencia(
            alumno=alumno,
            estado=EstadoAsistencia.PENDIENTE,
            hora_llegada=None,
            es_retardo=False,
            numero_equipo=None,
            es_laptop=False,
            origen=Origen.TABLETA,
        )

    def _anotar(self, accion: str, detalle: str) -> None:
        self._auditoria.anotar(accion, detalle)
