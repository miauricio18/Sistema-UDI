from datetime import datetime, timedelta

import pytest

from udi.excepciones import (
    DatosInvalidos,
    GrupoNoEncontrado,
    HorarioEmpalmado,
    LaboratorioNoEncontrado,
    SesionNoEncontrada,
)
from udi.modelos import EstadoSesion

MANANA = datetime(2026, 11, 17, 8, 0)


def prueba_crear_clase_dura_noventa_minutos(servicios):
    clase = servicios.horario.crear_clase("3CM1", "L1", MANANA)
    assert clase.hora_fin - clase.hora_inicio == timedelta(minutes=90)
    assert clase.estado is EstadoSesion.PROGRAMADA
    assert clase in servicios.horario.listar_dia(MANANA.date())


def prueba_no_se_empalman_clases_en_el_mismo_laboratorio(servicios):
    servicios.horario.crear_clase("3CM1", "L1", MANANA)
    with pytest.raises(HorarioEmpalmado):
        servicios.horario.crear_clase("3CM2", "L1", MANANA + timedelta(minutes=60))
    servicios.horario.crear_clase("3CM2", "L2", MANANA + timedelta(minutes=60))  # otro laboratorio sí
    servicios.horario.crear_clase("5CV1", "L1", MANANA + timedelta(minutes=90))  # justo al terminar sí


def prueba_datos_que_no_existen(servicios):
    with pytest.raises(GrupoNoEncontrado):
        servicios.horario.crear_clase("9ZZ9", "L1", MANANA)
    with pytest.raises(LaboratorioNoEncontrado):
        servicios.horario.crear_clase("3CM1", "L9", MANANA)
    with pytest.raises(DatosInvalidos):
        servicios.horario.crear_clase("3CM1", "L1", MANANA, MANANA)  # termina cuando empieza
    with pytest.raises(DatosInvalidos):
        servicios.horario.crear_clase("3CM1", "L1", "mañana a las 8")


def prueba_editar_no_choca_consigo_misma(servicios):
    clase = servicios.horario.crear_clase("3CM1", "L1", MANANA)
    movida = servicios.horario.editar_clase(
        clase.id_sesion, "3CM1", "L1", MANANA + timedelta(minutes=30)
    )
    assert movida.hora_inicio == MANANA + timedelta(minutes=30)


def prueba_cancelar_no_borra_pero_la_quita_del_dia(servicios):
    clase = servicios.horario.crear_clase("3CM1", "L1", MANANA)
    servicios.horario.cancelar_clase(clase.id_sesion)
    assert servicios.horario.listar_dia(MANANA.date()) == []
    fila = servicios.base_datos.uno("SELECT estado FROM sesion WHERE id_sesion = ?", (clase.id_sesion,))
    assert fila["estado"] == "CANCELADA"
    with pytest.raises(SesionNoEncontrada):
        servicios.horario.cancelar_clase(clase.id_sesion)
    servicios.horario.crear_clase("3CM2", "L1", MANANA)  # el hueco queda libre


def prueba_una_clase_cerrada_no_se_modifica(servicios):
    actual = servicios.asistencia.obtener_sesion_actual()
    servicios.asistencia.terminar_pase_lista(actual.id_sesion)
    with pytest.raises(DatosInvalidos):
        servicios.horario.cancelar_clase(actual.id_sesion)
