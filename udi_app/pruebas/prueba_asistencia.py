import pytest

from conftest import BOLETA_3CM1, BOLETA_3CM2
from udi.excepciones import AlumnoNoEncontrado, GrupoDistinto, PaseListaCerrado
from udi.modelos import EstadoAsistencia, EstadoSesion, Origen


def prueba_la_clase_actual_es_la_que_ya_empezo(clase):
    assert clase.grupo.clave_grupo == "3CM1"
    assert clase.id_laboratorio == "L1"


def prueba_la_lista_empieza_con_todos_pendientes(servicios, clase):
    lista = servicios.asistencia.obtener_lista(clase.id_sesion)
    assert len(lista) == 12
    assert {a.estado for a in lista} == {EstadoAsistencia.PENDIENTE}


def prueba_llegada_a_tiempo(servicios, clase, reloj):
    asistencia = servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    assert asistencia.estado is EstadoAsistencia.LLEGO
    assert asistencia.es_retardo is False
    assert asistencia.hora_llegada == reloj.ahora()
    assert asistencia.origen is Origen.TABLETA


def prueba_en_el_minuto_diez_exacto_todavia_no_es_retardo(servicios, clase, reloj):
    reloj.avanzar(5)  # 8:05 = 7:55 + 10 min
    asistencia = servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    assert asistencia.estado is EstadoAsistencia.LLEGO


def prueba_despues_de_diez_minutos_es_retardo(servicios, clase, reloj):
    reloj.avanzar(6)  # 8:06
    asistencia = servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    assert asistencia.estado is EstadoAsistencia.RETARDO
    assert asistencia.es_retardo is True


def prueba_registrar_dos_veces_no_cambia_la_primera_llegada(servicios, clase, reloj):
    primera = servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    reloj.avanzar(30)
    segunda = servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    assert segunda == primera


def prueba_la_primera_llegada_pone_la_clase_en_curso(servicios, clase):
    assert clase.estado is EstadoSesion.PROGRAMADA
    servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    assert servicios.asistencia.obtener_sesion_actual().estado is EstadoSesion.EN_CURSO


@pytest.mark.parametrize("boleta", ["9999999999", "", "abc", "1' OR '1'='1", "2026010001; DROP TABLE alumno"])
def prueba_boleta_desconocida_o_mal_escrita(servicios, clase, boleta):
    with pytest.raises(AlumnoNoEncontrado):
        servicios.asistencia.registrar_llegada(clase.id_sesion, boleta)


def prueba_alumno_de_otro_grupo_dice_que_clase_le_toca(servicios, clase):
    with pytest.raises(GrupoDistinto) as error:
        servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM2)
    assert "Bases de Datos" in error.value.mensaje
    assert "L2" in error.value.clase_que_le_toca


def prueba_terminar_pone_faltas_y_cierra(servicios, clase):
    servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    final = servicios.asistencia.terminar_pase_lista(clase.id_sesion)
    estados = [a.estado for a in final]
    assert estados.count(EstadoAsistencia.FALTA) == 11
    assert estados.count(EstadoAsistencia.LLEGO) == 1
    with pytest.raises(PaseListaCerrado):
        servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)


def prueba_reabrir_quita_las_faltas(servicios, clase):
    servicios.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    servicios.asistencia.terminar_pase_lista(clase.id_sesion)
    reabierta = servicios.asistencia.reabrir_pase_lista(clase.id_sesion)
    assert reabierta.estado is EstadoSesion.EN_CURSO
    estados = [a.estado for a in servicios.asistencia.obtener_lista(clase.id_sesion)]
    assert estados.count(EstadoAsistencia.PENDIENTE) == 11
    assert EstadoAsistencia.FALTA not in estados
