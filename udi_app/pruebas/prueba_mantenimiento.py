import pytest

from conftest import BOLETA_3CM1, OTRA_BOLETA_3CM1
from udi.excepciones import ErrorRespaldo, RespaldoInvalido
from udi.modelos import EstadoAsistencia


def _estado(sistema, id_sesion, boleta):
    lista = sistema.asistencia.obtener_lista(id_sesion)
    return next(a.estado for a in lista if a.alumno.boleta == boleta)


def prueba_terminar_el_pase_deja_un_respaldo(en_disco):
    assert en_disco.mantenimiento.listar_respaldos() == []
    clase = en_disco.asistencia.obtener_sesion_actual()
    en_disco.asistencia.terminar_pase_lista(clase.id_sesion)
    respaldos = en_disco.mantenimiento.listar_respaldos()
    assert len(respaldos) == 1
    assert respaldos[0].ruta.name == "udi_20261116_080000.db"
    assert respaldos[0].tamano_bytes > 0


def prueba_solo_se_conservan_los_mas_recientes(en_disco, reloj):
    for _ in range(4):
        reloj.avanzar(1)
        en_disco.mantenimiento.respaldar_ahora()
    assert en_disco.mantenimiento.limpiar_respaldos(conservar=2) == 2
    nombres = [r.ruta.name for r in en_disco.mantenimiento.listar_respaldos()]
    assert nombres == ["udi_20261116_080400.db", "udi_20261116_080300.db"]


def prueba_dos_respaldos_en_el_mismo_segundo_no_se_pisan(en_disco):
    en_disco.mantenimiento.respaldar_ahora()
    en_disco.mantenimiento.respaldar_ahora()
    assert len(en_disco.mantenimiento.listar_respaldos()) == 2


def prueba_restaurar_regresa_al_momento_del_respaldo(en_disco, reloj):
    clase = en_disco.asistencia.obtener_sesion_actual()
    en_disco.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    respaldo = en_disco.mantenimiento.respaldar_ahora()
    reloj.avanzar(1)
    en_disco.asistencia.registrar_llegada(clase.id_sesion, OTRA_BOLETA_3CM1)

    en_disco.mantenimiento.restaurar_respaldo(respaldo.ruta)

    assert _estado(en_disco, clase.id_sesion, BOLETA_3CM1) is EstadoAsistencia.LLEGO
    assert _estado(en_disco, clase.id_sesion, OTRA_BOLETA_3CM1) is EstadoAsistencia.PENDIENTE
    assert en_disco.mantenimiento.ver_bitacora(1)[0].accion == "RESTAURAR"
    assert len(en_disco.mantenimiento.listar_respaldos()) == 2  # se guardó copia de lo que había


def prueba_un_archivo_cualquiera_no_se_restaura(en_disco, tmp_path):
    falso = tmp_path / "falso.db"
    falso.write_text("esto no es una base de datos", encoding="utf-8")
    with pytest.raises(RespaldoInvalido):
        en_disco.mantenimiento.restaurar_respaldo(falso)
    with pytest.raises(RespaldoInvalido):
        en_disco.mantenimiento.restaurar_respaldo(tmp_path / "no_existe.db")
    assert en_disco.asistencia.obtener_sesion_actual()  # la base sigue intacta


def prueba_estado_del_sistema(en_disco):
    estado = en_disco.mantenimiento.estado_sistema()
    assert estado.integridad_ok
    assert estado.total_alumnos == 36
    assert estado.total_clases == 3
    assert estado.ultimo_respaldo is None
    assert en_disco.mantenimiento.verificar_integridad() == []
    en_disco.mantenimiento.compactar()


def prueba_la_base_de_ejemplo_en_memoria_no_se_respalda(servicios):
    with pytest.raises(ErrorRespaldo):
        servicios.mantenimiento.respaldar_ahora()


def prueba_el_log_registra_las_acciones(en_disco, tmp_path):
    clase = en_disco.asistencia.obtener_sesion_actual()
    en_disco.asistencia.registrar_llegada(clase.id_sesion, BOLETA_3CM1)
    for salida in en_disco.logger.handlers:
        salida.flush()
    texto = (tmp_path / "UDI" / "logs" / "udi.log").read_text(encoding="utf-8")
    assert "Aplicación iniciada" in texto
    assert "LLEGADA" in texto
