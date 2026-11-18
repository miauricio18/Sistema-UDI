"""La interfaz completa, sin que nadie toque la pantalla.

Cada prueba abre la aplicación real sobre los datos de ejemplo y llama a los
mismos métodos que llaman los botones. Los diálogos se sustituyen por
respuestas fijas. Si la máquina no tiene pantalla, estas pruebas se saltan.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import pytest

from conftest import BOLETA_3CM1, BOLETA_3CM2, OTRA_BOLETA_3CM1
from udi.aplicacion import iniciar
from udi.configuracion import Configuracion
from udi.modelos import EstadoAsistencia, EstadoEquipo, EstadoMaestro, EstadoSesion, Origen, TipoReporte

tk = pytest.importorskip("tkinter")

from interfaz.app import Aplicacion  # noqa: E402
from interfaz.pantallas import PANTALLAS  # noqa: E402
from interfaz.pantallas.administracion import (  # noqa: E402
    PestanaDatos,
    PestanaLaboratorios,
    PestanaSistema,
)


def _abrir(servicios) -> Aplicacion:
    try:
        aplicacion = Aplicacion(servicios)
    except tk.TclError:
        pytest.skip("No hay pantalla disponible para abrir la ventana.")
    aplicacion.textos_mostrados: List[Tuple[str, str]] = []
    aplicacion.contexto.confirmar = lambda *_a, **_k: True
    aplicacion.contexto.mostrar_texto = lambda titulo, texto: aplicacion.textos_mostrados.append(
        (titulo, texto))
    aplicacion.raiz.update()
    return aplicacion


@pytest.fixture
def app(servicios):
    aplicacion = _abrir(servicios)
    yield aplicacion
    aplicacion.raiz.destroy()


@pytest.fixture
def app_en_disco(en_disco):
    aplicacion = _abrir(en_disco)
    yield aplicacion
    aplicacion.raiz.destroy()


def _aviso(aplicacion) -> str:
    return aplicacion.avisos.ultimo[0]


def _asistencia(aplicacion, boleta):
    servicios = aplicacion.contexto.servicios
    clase = servicios.asistencia.obtener_sesion_actual()
    return next(a for a in servicios.asistencia.obtener_lista(clase.id_sesion)
                if a.alumno.boleta == boleta)


# --------------------------------------------------------------------------- #
# Navegación
# --------------------------------------------------------------------------- #
def prueba_todas_las_pantallas_abren(app):
    for clase in PANTALLAS:
        pantalla = app.mostrar(clase.clave)
        app.raiz.update()
        assert pantalla.winfo_ismapped()
    assert len({clase.clave for clase in PANTALLAS}) == len(PANTALLAS)


def prueba_una_tableta_recien_instalada_abre_sin_datos(tmp_path, reloj):
    """Base vacía: ninguna pantalla falla y el camino de alta funciona desde la interfaz."""
    servicios = iniciar(Configuracion(carpeta_datos=tmp_path / "UDI"), reloj=reloj)
    app = _abrir(servicios)
    try:
        for clase in PANTALLAS:
            app.mostrar(clase.clave)
            app.raiz.update()
        assert app.pantalla("pase_lista")._sesion is None
        app.pantalla("horario").nueva_clase()            # sin grupos todavía: solo orienta
        assert _aviso(app) == "info"

        administracion = app.mostrar("administracion")
        assert administracion.pestana(PestanaLaboratorios).guardar_laboratorio("L1", "UDI 1", "30")
        lista = tmp_path / "lista.csv"
        lista.write_text("boleta,nombre,grupo,materia,maestro\n"
                         "2027000001,Ana Ruiz,1CM1,Algoritmos,Mtro. Paz\n", encoding="utf-8")
        assert administracion.pestana(PestanaDatos).importar(
            servicios.archivos.importar_lista, lista, "alumnos")
        assert app.pantalla("horario").guardar_clase(
            {"grupo": "1CM1", "laboratorio": "L1", "fecha": "16/11/2026", "inicio": "08:00", "fin": ""})
        pase = app.mostrar("pase_lista")
        pase._boleta.set("2027000001")
        pase.registrar_llegada()
        pase.tocar_equipo(30)
        assert servicios.asistencia.obtener_lista(pase._sesion.id_sesion)[0].numero_equipo == 30
    finally:
        app.raiz.destroy()
        servicios.cerrar()
        for salida in list(servicios.logger.handlers):
            servicios.logger.removeHandler(salida)
            salida.close()


def prueba_un_error_de_programacion_no_cierra_la_aplicacion(app_en_disco):
    app = app_en_disco
    try:
        raise RuntimeError("fallo de prueba")
    except RuntimeError as error:
        app.raiz.report_callback_exception(type(error), error, error.__traceback__)
    assert _aviso(app) == "error"
    servicios = app.contexto.servicios
    for salida in servicios.logger.handlers:
        salida.flush()
    registro = (servicios.mantenimiento.estado_sistema().ruta_base_datos)
    texto = (Path(registro).parent / "logs" / "udi.log").read_text(encoding="utf-8")
    assert "Error no controlado en la interfaz" in texto and "fallo de prueba" in texto
    app.mostrar("horario")                              # la aplicación sigue funcionando


# --------------------------------------------------------------------------- #
# Pase de lista
# --------------------------------------------------------------------------- #
def prueba_registrar_y_asignar_en_tres_toques(app):
    pantalla = app.pantalla("pase_lista")
    pantalla._boleta.set(BOLETA_3CM1)
    pantalla.registrar_llegada()
    assert pantalla._boleta.get() == ""                 # lista para la siguiente boleta
    assert pantalla._boleta_elegida == BOLETA_3CM1      # el alumno queda seleccionado
    pantalla.tocar_equipo(5)
    asistencia = _asistencia(app, BOLETA_3CM1)
    assert asistencia.estado is EstadoAsistencia.LLEGO
    assert asistencia.numero_equipo == 5
    assert asistencia.origen is Origen.TABLETA
    assert pantalla._boleta_elegida is None             # sigue el próximo alumno
    assert _aviso(app) == "exito"


def prueba_boleta_desconocida_avisa_y_no_borra_lo_escrito(app):
    pantalla = app.pantalla("pase_lista")
    pantalla._boleta.set("999")
    pantalla.registrar_llegada()
    assert _aviso(app) == "error"
    assert pantalla._boleta.get() == "999"


def prueba_alumno_de_otro_grupo_avisa(app):
    pantalla = app.pantalla("pase_lista")
    pantalla._boleta.set(BOLETA_3CM2)
    pantalla.registrar_llegada()
    assert _aviso(app) == "error"


def prueba_sin_boleta_ni_seleccion_solo_orienta(app):
    pantalla = app.pantalla("pase_lista")
    pantalla.registrar_llegada()
    assert _aviso(app) == "info"
    pantalla.tocar_equipo(5)
    assert _aviso(app) == "info"
    assert _asistencia(app, BOLETA_3CM1).estado is EstadoAsistencia.PENDIENTE


def prueba_elegir_en_la_lista_registra_como_manual(app):
    pantalla = app.pantalla("pase_lista")
    pantalla.seleccionar_alumno(BOLETA_3CM1)
    pantalla.registrar_llegada()
    asistencia = _asistencia(app, BOLETA_3CM1)
    assert asistencia.estado is EstadoAsistencia.LLEGO
    assert asistencia.origen is Origen.MANUAL


def prueba_computadora_ocupada_o_fuera_de_servicio(app):
    pantalla = app.pantalla("pase_lista")
    pantalla.seleccionar_alumno(BOLETA_3CM1)
    pantalla.tocar_equipo(5)
    pantalla.seleccionar_alumno(OTRA_BOLETA_3CM1)
    pantalla.tocar_equipo(5)
    assert _aviso(app) == "error"
    pantalla.tocar_equipo(40)                           # la 40 está fuera de servicio
    assert _aviso(app) == "error"
    assert _asistencia(app, OTRA_BOLETA_3CM1).numero_equipo is None


def prueba_tocar_una_computadora_ocupada_selecciona_a_quien_la_usa(app):
    pantalla = app.pantalla("pase_lista")
    pantalla.seleccionar_alumno(BOLETA_3CM1)
    pantalla.tocar_equipo(5)
    assert pantalla._boleta_elegida is None
    pantalla.tocar_equipo(5)
    assert pantalla._boleta_elegida == BOLETA_3CM1


def prueba_laptop_y_quitar_equipo(app):
    pantalla = app.pantalla("pase_lista")
    pantalla.seleccionar_alumno(BOLETA_3CM1)
    pantalla.tocar_equipo(5)
    pantalla.seleccionar_alumno(BOLETA_3CM1)
    pantalla.alternar_laptop()
    assert _asistencia(app, BOLETA_3CM1).es_laptop
    assert _asistencia(app, BOLETA_3CM1).numero_equipo == 5   # la laptop no quita el lugar
    pantalla.alternar_laptop()
    assert not _asistencia(app, BOLETA_3CM1).es_laptop
    assert _asistencia(app, BOLETA_3CM1).numero_equipo == 5
    pantalla.tocar_equipo(6)
    pantalla.seleccionar_alumno(BOLETA_3CM1)
    pantalla.liberar_equipo()
    assert _asistencia(app, BOLETA_3CM1).numero_equipo is None


def prueba_marcar_al_maestro(app):
    pantalla = app.pantalla("pase_lista")
    pantalla.marcar_maestro(EstadoMaestro.AVISO)
    assert app.contexto.servicios.asistencia.obtener_sesion_actual().estado_maestro is EstadoMaestro.AVISO
    assert pantalla._maestro.valor is EstadoMaestro.AVISO


def prueba_terminar_pide_confirmacion_y_se_puede_reabrir(app):
    pantalla = app.pantalla("pase_lista")
    clase = pantalla._sesion
    app.contexto.confirmar = lambda *_a, **_k: False
    pantalla.terminar_pase()
    assert pantalla._sesion.estado is not EstadoSesion.CERRADA

    app.contexto.confirmar = lambda *_a, **_k: True
    pantalla.terminar_pase()
    assert pantalla._sesion.id_sesion == clase.id_sesion        # se queda a la vista
    assert pantalla._sesion.estado is EstadoSesion.CERRADA
    pantalla._boleta.set(BOLETA_3CM1)
    pantalla.registrar_llegada()
    assert _aviso(app) == "error"                               # cerrada: no acepta llegadas

    pantalla.reabrir_pase()
    assert pantalla._sesion.estado is EstadoSesion.EN_CURSO


def prueba_elegir_otra_clase_del_dia(app):
    pantalla = app.pantalla("pase_lista")
    otra = next(s for s in pantalla._clases_del_dia if s.grupo.clave_grupo == "3CM2")
    pantalla.elegir_clase(otra.id_sesion)
    pantalla._boleta.set(BOLETA_3CM2)
    pantalla.registrar_llegada()
    assert _aviso(app) == "exito"
    assert pantalla._sesion.id_sesion == otra.id_sesion


def prueba_un_dia_sin_clases_muestra_el_aviso_y_no_falla(app, reloj):
    reloj.avanzar(60 * 24 * 3)
    pantalla = app.mostrar("pase_lista")
    app.raiz.update()
    assert pantalla._sesion is None
    assert pantalla._vacio.winfo_ismapped()
    pantalla.registrar_llegada()                                # los botones no hacen nada
    pantalla.tocar_equipo(1)


# --------------------------------------------------------------------------- #
# Horario
# --------------------------------------------------------------------------- #
_CLASE_NUEVA = {"grupo": "3CM1  ·  POO", "laboratorio": "L2  ·  UDI 2",
                "fecha": "17/11/2026", "inicio": "07:00", "fin": ""}


def prueba_crear_cambiar_y_cancelar_una_clase(app):
    pantalla = app.mostrar("horario")
    assert pantalla.guardar_clase(_CLASE_NUEVA)
    assert pantalla._dia == datetime(2026, 11, 17).date()       # salta al día de la clase
    clase = pantalla._clases[0]
    assert (clase.hora_fin - clase.hora_inicio).seconds == 90 * 60

    assert pantalla.guardar_clase({**_CLASE_NUEVA, "inicio": "09:00", "fin": "10:00"}, clase.id_sesion)
    assert pantalla._clases[0].hora_inicio.hour == 9

    pantalla._tabla.cargar([], None)
    pantalla.actualizar()
    pantalla._tabla._arbol.selection_set(str(clase.id_sesion))
    pantalla.cancelar_clase()
    assert pantalla._clases == []


@pytest.mark.parametrize("cambio", [
    {"inicio": "25:00"}, {"fecha": "ayer"}, {"inicio": "10:00", "fin": "09:00"},
    {"fecha": "16/11/2026", "inicio": "08:00", "laboratorio": "L1  ·  UDI 1"},   # empalme
])
def prueba_clase_mal_capturada_avisa_y_no_guarda(app, cambio):
    pantalla = app.mostrar("horario")
    assert not pantalla.guardar_clase({**_CLASE_NUEVA, **cambio})
    assert _aviso(app) == "error"


# --------------------------------------------------------------------------- #
# Reportes
# --------------------------------------------------------------------------- #
def prueba_reporte_de_falla_y_reactivacion(app):
    pantalla = app.mostrar("reportes")
    pantalla._equipo.set("7")
    pantalla._texto.insert("1.0", "No enciende el monitor.")
    assert pantalla.guardar_reporte()
    servicios = app.contexto.servicios
    clase = servicios.asistencia.obtener_sesion_actual()
    estado = {e.numero: e.estado for e in servicios.asistencia.mapa_laboratorio(clase.id_sesion)}
    assert estado[7] is EstadoEquipo.FUERA_DE_SERVICIO
    assert pantalla._texto.get("1.0", "end").strip() == ""      # formulario limpio

    assert pantalla.reactivar("L1", "7")
    estado = {e.numero: e.estado for e in servicios.asistencia.mapa_laboratorio(clase.id_sesion)}
    assert estado[7] is EstadoEquipo.LIBRE


def prueba_una_observacion_no_saca_equipos_y_exige_texto(app):
    pantalla = app.mostrar("reportes")
    pantalla.elegir_tipo(TipoReporte.OBSERVACION)
    assert not pantalla.guardar_reporte()                       # sin texto
    assert _aviso(app) == "error"
    pantalla._texto.insert("1.0", "Faltan sillas.")
    assert pantalla.guardar_reporte()
    assert app.contexto.servicios.reportes.listar_reportes()[0].tipo is TipoReporte.OBSERVACION
    assert not pantalla.reactivar("L1", "siete")


# --------------------------------------------------------------------------- #
# Estadísticas
# --------------------------------------------------------------------------- #
def prueba_estadisticas_y_exportar(app_en_disco):
    app = app_en_disco
    pase = app.pantalla("pase_lista")
    pase.seleccionar_alumno(BOLETA_3CM1)
    pase.registrar_llegada()
    pantalla = app.mostrar("estadisticas")
    app.raiz.update()
    assert pantalla.grupo_elegido().clave_grupo == "3CM1"
    assert len(pantalla._tabla.identificadores()) == 3
    ruta = pantalla.exportar()
    assert ruta.exists() and ruta.suffix == ".xlsx"
    assert _aviso(app) == "exito"


# --------------------------------------------------------------------------- #
# Administración
# --------------------------------------------------------------------------- #
def prueba_importar_lista_buena_y_lista_con_errores(app, tmp_path):
    pantalla = app.mostrar("administracion")
    datos = pantalla.pestana(PestanaDatos)
    servicios = app.contexto.servicios

    buena = tmp_path / "lista.csv"
    buena.write_text("boleta,nombre,grupo\n2027000001,Ana Ruiz,3CM1\n", encoding="utf-8")
    assert datos.importar(servicios.archivos.importar_lista, buena, "alumnos")
    assert _aviso(app) == "exito"

    mala = tmp_path / "mala.csv"
    mala.write_text("boleta,nombre,grupo\n2027000002,Luis Paz,3CM1\nx,Sin Boleta,3CM1\n", encoding="utf-8")
    assert not datos.importar(servicios.archivos.importar_lista, mala, "alumnos")
    assert "Fila 3" in app.textos_mostrados[0][1]
    assert servicios.base_datos.uno("SELECT 1 FROM alumno WHERE boleta = '2027000002'") is None

    assert not datos.importar(servicios.archivos.importar_lista, tmp_path / "no_existe.csv", "alumnos")
    assert _aviso(app) == "error"


def prueba_alta_de_laboratorio(app):
    pantalla = app.mostrar("administracion")
    pantalla.elegir_pestana(1)
    laboratorios = pantalla.pestana(PestanaLaboratorios)
    assert laboratorios.guardar_laboratorio("L3", "UDI 3", "25")
    assert "L3" in laboratorios._tabla.identificadores()
    assert not laboratorios.guardar_laboratorio("L4", "UDI 4", "muchas")
    assert _aviso(app) == "error"


def prueba_respaldar_y_restaurar(app_en_disco):
    app = app_en_disco
    pantalla = app.mostrar("administracion")
    pantalla.elegir_pestana(2)
    sistema = pantalla.pestana(PestanaSistema)
    respaldo = sistema.respaldar()
    assert respaldo.ruta.exists()

    pase = app.pantalla("pase_lista")
    pase.actualizar()
    pase.seleccionar_alumno(BOLETA_3CM1)
    pase.registrar_llegada()
    assert sistema.restaurar(respaldo.ruta)
    assert _asistencia(app, BOLETA_3CM1).estado is EstadoAsistencia.PENDIENTE


def prueba_en_memoria_no_se_puede_respaldar_y_se_avisa(app):
    pantalla = app.mostrar("administracion")
    sistema = pantalla.pestana(PestanaSistema)
    assert sistema.respaldar() is None
    assert _aviso(app) == "error"


# --------------------------------------------------------------------------- #
# Diálogos reales (los que las demás pruebas sustituyen)
# --------------------------------------------------------------------------- #
def _responder(aplicacion, accion: str) -> None:
    """Programa que el diálogo abierto se acepte o cancele solo, un instante después."""
    def actuar() -> None:
        abiertos = [v for v in aplicacion.raiz.winfo_children() if isinstance(v, tk.Toplevel)]
        getattr(abiertos[-1], accion)()
    aplicacion.raiz.after(100, actuar)


def prueba_dialogo_de_confirmacion(app):
    from interfaz.componentes import dialogos

    _responder(app, "aceptar")
    assert dialogos.confirmar(app.raiz, "Terminar", "¿Seguro?") is True
    _responder(app, "cancelar")
    assert dialogos.confirmar(app.raiz, "Terminar", "¿Seguro?", peligro=True) is False


def prueba_dialogo_de_formulario(app):
    from interfaz.componentes import dialogos

    campos = (dialogos.Campo("clave", "Clave", " L3 "),
              dialogos.Campo("tipo", "Tipo", "A", ("A", "B"), ayuda="Elige uno"))
    _responder(app, "aceptar")
    assert dialogos.pedir_datos(app.raiz, "Laboratorio", campos) == {"clave": "L3", "tipo": "A"}
    _responder(app, "cancelar")
    assert dialogos.pedir_datos(app.raiz, "Laboratorio", campos) is None
    _responder(app, "aceptar")
    dialogos.mostrar_texto(app.raiz, "Errores", "Fila 3: boleta no válida")
