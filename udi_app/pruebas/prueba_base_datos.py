import sqlite3

import pytest

from udi import base_datos
from udi.base_datos import ESQUEMA, VERSION_ESQUEMA, BaseDatos
from udi.configuracion import Configuracion
from udi.excepciones import ErrorUDI


@pytest.fixture
def base():
    bd = BaseDatos(Configuracion.para_memoria())
    bd.crear_tablas()
    yield bd
    bd.cerrar()


def _laboratorios(bd):
    return bd.uno("SELECT COUNT(*) FROM laboratorio")[0]


def prueba_si_hay_error_se_deshace_todo(base):
    with pytest.raises(RuntimeError):
        with base.transaccion():
            base.ejecutar("INSERT INTO laboratorio (id_laboratorio, nombre) VALUES ('L1', 'UDI 1')")
            raise RuntimeError("se fue la luz")
    assert _laboratorios(base) == 0


def prueba_transacciones_anidadas_se_guardan_juntas(base):
    with base.transaccion():
        base.ejecutar("INSERT INTO laboratorio (id_laboratorio, nombre) VALUES ('L1', 'UDI 1')")
        with base.transaccion():
            base.ejecutar("INSERT INTO laboratorio (id_laboratorio, nombre) VALUES ('L2', 'UDI 2')")
    assert _laboratorios(base) == 2


def prueba_error_en_la_de_adentro_deshace_tambien_la_de_afuera(base):
    with pytest.raises(RuntimeError):
        with base.transaccion():
            base.ejecutar("INSERT INTO laboratorio (id_laboratorio, nombre) VALUES ('L1', 'UDI 1')")
            with base.transaccion():
                raise RuntimeError("falla adentro")
    assert _laboratorios(base) == 0


def prueba_las_llaves_foraneas_estan_encendidas(base):
    with pytest.raises(sqlite3.IntegrityError):
        base.ejecutar("INSERT INTO asistencia (id_sesion, boleta, estado) VALUES (1, '000', 'LLEGO')")


def prueba_ocupado_no_se_puede_guardar(base):
    base.ejecutar("INSERT INTO laboratorio (id_laboratorio, nombre) VALUES ('L1', 'UDI 1')")
    with pytest.raises(sqlite3.IntegrityError):
        base.ejecutar("INSERT INTO equipo (id_laboratorio, numero, codigo, estado) VALUES ('L1', 1, 'L1-1', 'OCUPADO')")


def prueba_base_nueva_queda_en_la_ultima_version(base):
    assert base.version_esquema == VERSION_ESQUEMA
    assert base.verificar_integridad() == []


def prueba_una_base_vieja_se_actualiza_sola_sin_perder_datos(tmp_path, monkeypatch):
    configuracion = Configuracion(carpeta_datos=tmp_path)
    vieja = sqlite3.connect(configuracion.ruta_bd)  # como la dejaba la entrega anterior
    vieja.executescript(ESQUEMA)
    vieja.execute("INSERT INTO bitacora (fecha_hora, accion) VALUES ('2026-11-01T08:00:00', 'VIEJO')")
    vieja.commit()
    vieja.close()

    # Una migración de prueba, como la que se agregaría el día que cambie la estructura.
    migracion = base_datos.Migracion(
        1, "Prueba", ("ALTER TABLE bitacora ADD COLUMN origen TEXT NOT NULL DEFAULT ''",)
    )
    monkeypatch.setattr(base_datos, "MIGRACIONES", (migracion,))
    monkeypatch.setattr(base_datos, "VERSION_ESQUEMA", 1)

    bd = BaseDatos(configuracion)
    try:
        bd.crear_tablas()
        bd.crear_tablas()  # aplicarla dos veces no rompe nada
        assert bd.version_esquema == 1
        fila = bd.uno("SELECT accion, origen FROM bitacora")
        assert (fila["accion"], fila["origen"]) == ("VIEJO", "")
    finally:
        bd.cerrar()


def prueba_una_base_mas_nueva_que_el_programa_no_se_toca(tmp_path):
    configuracion = Configuracion(carpeta_datos=tmp_path)
    futura = sqlite3.connect(configuracion.ruta_bd)
    futura.execute(f"PRAGMA user_version = {VERSION_ESQUEMA + 1}")
    futura.close()
    bd = BaseDatos(configuracion)
    try:
        with pytest.raises(ErrorUDI) as error:
            bd.crear_tablas()
        assert error.value.codigo == "base_mas_nueva"
    finally:
        bd.cerrar()
