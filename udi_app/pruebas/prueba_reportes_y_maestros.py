import pytest

from conftest import BOLETA_3CM1
from udi.excepciones import DatosInvalidos, EquipoNoEncontrado, LaboratorioNoEncontrado
from udi.modelos import EstadoEquipo, EstadoMaestro, TipoReporte
from udi.servicios.maestros import ServicioMaestros


def prueba_una_falla_saca_el_equipo_y_deja_libre_al_alumno(servicios, clase):
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 5)
    reporte = servicios.reportes.crear_reporte(
        TipoReporte.FALLA_EQUIPO, "L1", "No enciende", 5, poner_fuera_de_servicio=True
    )
    assert reporte.numero_equipo == 5
    assert reporte.ultimo_usuario  # se guarda quién la usó por última vez
    mapa = {e.numero: e for e in servicios.asistencia.mapa_laboratorio(clase.id_sesion)}
    assert mapa[5].estado is EstadoEquipo.FUERA_DE_SERVICIO
    lista = servicios.asistencia.obtener_lista(clase.id_sesion)
    assert next(a for a in lista if a.alumno.boleta == BOLETA_3CM1).numero_equipo is None


def prueba_reportes_del_mas_nuevo_al_mas_viejo(servicios, reloj):
    servicios.reportes.crear_reporte(TipoReporte.OBSERVACION, "L1", "Primero")
    reloj.avanzar(1)
    servicios.reportes.crear_reporte(TipoReporte.INCIDENTE, "L2", "Segundo")
    assert [r.texto for r in servicios.reportes.listar_reportes()] == ["Segundo", "Primero"]


@pytest.mark.parametrize(
    "argumentos",
    [
        (TipoReporte.OBSERVACION, "L1", "   "),            # sin texto
        (TipoReporte.OBSERVACION, "L1", "x" * 501),        # demasiado largo
        (TipoReporte.FALLA_EQUIPO, "L1", "Falla"),         # falla sin computadora
        ("CHISME", "L1", "Texto"),                         # tipo inventado
        (TipoReporte.OBSERVACION, "L 1;", "Texto"),        # laboratorio mal escrito
    ],
)
def prueba_reporte_con_datos_invalidos(servicios, argumentos):
    with pytest.raises(DatosInvalidos):
        servicios.reportes.crear_reporte(*argumentos)


def prueba_reporte_de_lugares_que_no_existen(servicios):
    with pytest.raises(LaboratorioNoEncontrado):
        servicios.reportes.crear_reporte(TipoReporte.OBSERVACION, "L9", "Texto")
    with pytest.raises(EquipoNoEncontrado):
        servicios.reportes.crear_reporte(TipoReporte.FALLA_EQUIPO, "L1", "Texto", 99)


def prueba_reactivar_un_equipo(servicios):
    servicios.reportes.reactivar_equipo("L1", 40)
    clase = servicios.asistencia.obtener_sesion_actual()
    mapa = {e.numero: e for e in servicios.asistencia.mapa_laboratorio(clase.id_sesion)}
    assert mapa[40].estado is EstadoEquipo.LIBRE


def prueba_marcar_al_maestro(servicios, clase):
    assert clase.estado_maestro is EstadoMaestro.SIN_ANOTAR
    sesion = servicios.maestros.marcar_maestro(clase.id_sesion, EstadoMaestro.AVISO)
    assert sesion.estado_maestro is EstadoMaestro.AVISO
    with pytest.raises(DatosInvalidos):
        servicios.maestros.marcar_maestro(clase.id_sesion, "TAL VEZ")


def prueba_aviso_cuenta_como_cumplido():
    assert ServicioMaestros.cumplio(EstadoMaestro.VINO)
    assert ServicioMaestros.cumplio(EstadoMaestro.AVISO)
    assert not ServicioMaestros.cumplio(EstadoMaestro.NO_VINO)
    assert not ServicioMaestros.cumplio(EstadoMaestro.SIN_ANOTAR)
