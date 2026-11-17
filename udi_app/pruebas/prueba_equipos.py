import pytest

from conftest import BOLETA_3CM1, OTRA_BOLETA_3CM1
from udi.excepciones import (
    DatosInvalidos,
    EquipoFueraDeServicio,
    EquipoNoEncontrado,
    EquipoOcupado,
)
from udi.modelos import EstadoAsistencia, EstadoEquipo


def _equipo(sistema, clase, numero):
    return next(e for e in sistema.asistencia.mapa_laboratorio(clase.id_sesion) if e.numero == numero)


def prueba_asignar_registra_la_llegada_y_ocupa_el_equipo(servicios, clase):
    asistencia = servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 5)
    assert asistencia.numero_equipo == 5
    assert asistencia.estado is EstadoAsistencia.LLEGO
    equipo = _equipo(servicios, clase, 5)
    assert equipo.estado is EstadoEquipo.OCUPADO
    assert equipo.alumno_actual.boleta == BOLETA_3CM1


def prueba_equipo_ocupado_por_otro(servicios, clase):
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 5)
    with pytest.raises(EquipoOcupado):
        servicios.asistencia.asignar_equipo(clase.id_sesion, OTRA_BOLETA_3CM1, 5)


def prueba_si_la_asignacion_falla_no_queda_la_llegada_a_medias(servicios, clase):
    """Todo o nada: el error deshace también la llegada que se había registrado."""
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 5)
    with pytest.raises(EquipoOcupado):
        servicios.asistencia.asignar_equipo(clase.id_sesion, OTRA_BOLETA_3CM1, 5)
    lista = servicios.asistencia.obtener_lista(clase.id_sesion)
    otro = next(a for a in lista if a.alumno.boleta == OTRA_BOLETA_3CM1)
    assert otro.estado is EstadoAsistencia.PENDIENTE


def prueba_equipo_fuera_de_servicio(servicios, clase):
    with pytest.raises(EquipoFueraDeServicio):
        servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 40)


def prueba_equipo_que_no_existe(servicios, clase):
    with pytest.raises(EquipoNoEncontrado):
        servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 99)


@pytest.mark.parametrize("numero", ["5", 0, -1, 5.0, True, None, 1000])
def prueba_numero_de_equipo_invalido(servicios, clase, numero):
    with pytest.raises(DatosInvalidos):
        servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, numero)


def prueba_cambiar_de_equipo_libera_el_anterior(servicios, clase):
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 5)
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 6)
    assert _equipo(servicios, clase, 5).estado is EstadoEquipo.LIBRE
    assert _equipo(servicios, clase, 6).estado is EstadoEquipo.OCUPADO


def prueba_la_laptop_libera_la_computadora(servicios, clase):
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 5)
    asistencia = servicios.asistencia.marcar_laptop(clase.id_sesion, BOLETA_3CM1)
    assert asistencia.es_laptop is True
    assert asistencia.numero_equipo is None
    assert _equipo(servicios, clase, 5).estado is EstadoEquipo.LIBRE


def prueba_liberar_equipo(servicios, clase):
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 5)
    asistencia = servicios.asistencia.liberar_equipo(clase.id_sesion, BOLETA_3CM1)
    assert asistencia.numero_equipo is None
    assert asistencia.estado is EstadoAsistencia.LLEGO
