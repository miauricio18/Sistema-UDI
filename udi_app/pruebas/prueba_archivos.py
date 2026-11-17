import pytest
from openpyxl import Workbook, load_workbook

from conftest import BOLETA_3CM1, configuracion_de_prueba
from udi.aplicacion import iniciar
from udi.excepciones import ArchivoInvalido
from udi.modelos import Periodo


def _csv(carpeta, nombre, texto):
    ruta = carpeta / nombre
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _total_alumnos(sistema):
    return sistema.base_datos.uno("SELECT COUNT(*) FROM alumno")[0]


def prueba_importar_lista_crea_grupo_y_alumnos(servicios, tmp_path):
    ruta = _csv(tmp_path, "lista.csv",
                "Boleta;Nombre;Grupo;Materia;Profesor\n"
                "2027000001;Ana Prueba;9ZZ1;Química;Dr. Equis\n"
                "2027000002;Beto Prueba;9ZZ1;;\n")
    resumen = servicios.archivos.importar_lista(ruta)
    assert (resumen.agregados, resumen.actualizados, resumen.fue_exitosa) == (2, 0, True)
    assert servicios.archivos.importar_lista(ruta).actualizados == 2  # repetir no duplica


def prueba_un_error_y_no_se_guarda_nada(servicios, tmp_path):
    antes = _total_alumnos(servicios)
    ruta = _csv(tmp_path, "lista.csv",
                "boleta,nombre,clave_grupo\n"
                "2027000001,Ana Prueba,3CM1\n"
                "12,Boleta Corta,3CM1\n"
                "2027000003,,3CM1\n"
                "2027000004,Grupo Fantasma,8XX8\n")
    resumen = servicios.archivos.importar_lista(ruta)
    assert not resumen.fue_exitosa
    assert [e.numero_fila for e in resumen.filas_con_error] == [3, 4, 5]
    assert _total_alumnos(servicios) == antes


def prueba_excel_con_boleta_numerica(servicios, tmp_path):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["Boleta", "Nombre", "Clave grupo"])
    hoja.append([2027000009, "Número En Excel", "3CM1"])
    ruta = tmp_path / "lista.xlsx"
    libro.save(ruta)
    assert servicios.archivos.importar_lista(ruta).agregados == 1
    assert servicios.base_datos.uno("SELECT 1 FROM alumno WHERE boleta = '2027000009'")


@pytest.mark.parametrize(
    "nombre, texto",
    [
        ("lista.txt", "boleta,nombre,clave_grupo\n"),          # formato no aceptado
        ("lista.csv", ""),                                     # vacío
        ("lista.csv", "matricula,alumno\n2027000001,Ana\n"),   # falta la columna del grupo
    ],
)
def prueba_archivos_que_no_sirven(servicios, tmp_path, nombre, texto):
    with pytest.raises(ArchivoInvalido):
        servicios.archivos.importar_lista(_csv(tmp_path, nombre, texto))


def prueba_archivo_que_no_existe(servicios, tmp_path):
    with pytest.raises(ArchivoInvalido):
        servicios.archivos.importar_lista(tmp_path / "no_esta.csv")


def prueba_limites_de_tamano_y_filas(tmp_path, reloj):
    sistema = iniciar(configuracion_de_prueba(max_filas_archivo=2), datos_ejemplo=True, reloj=reloj)
    try:
        filas = "".join(f"202700000{i},Alumno {i},3CM1\n" for i in range(3))
        with pytest.raises(ArchivoInvalido):
            sistema.archivos.importar_lista(_csv(tmp_path, "l.csv", "boleta,nombre,clave_grupo\n" + filas))
    finally:
        sistema.cerrar()
    sistema = iniciar(configuracion_de_prueba(max_megas_archivo=0), datos_ejemplo=True, reloj=reloj)
    try:
        with pytest.raises(ArchivoInvalido):
            sistema.archivos.importar_lista(_csv(tmp_path, "l.csv", "boleta,nombre,clave_grupo\n"))
    finally:
        sistema.cerrar()


def prueba_importar_horario(servicios, tmp_path):
    ruta = _csv(tmp_path, "horario.csv",
                "fecha,hora,grupo,lab\n"
                "2026-11-18,08:00,3CM1,L1\n"
                "18/11/2026,10:00,3CM2,L1\n")
    resumen = servicios.archivos.importar_horario(ruta)
    assert (resumen.agregados, resumen.fue_exitosa) == (2, True)
    repetido = servicios.archivos.importar_horario(ruta)
    assert (repetido.agregados, repetido.actualizados) == (0, 2)


def prueba_horario_con_empalme_no_guarda_nada(servicios, tmp_path):
    ruta = _csv(tmp_path, "horario.csv",
                "fecha,hora,grupo,lab\n"
                "2026-11-18,08:00,3CM1,L1\n"
                "2026-11-18,08:30,3CM2,L1\n"
                "2026-11-18,25:00,3CM2,L2\n"
                "2026-11-18,12:00,3CM2,L7\n")
    resumen = servicios.archivos.importar_horario(ruta)
    assert [e.numero_fila for e in resumen.filas_con_error] == [3, 4, 5]
    assert servicios.base_datos.uno("SELECT COUNT(*) FROM sesion WHERE date(hora_inicio) = '2026-11-18'")[0] == 0


def prueba_exportar_excel(servicios, tmp_path):
    clase = servicios.asistencia.obtener_sesion_actual()
    servicios.asistencia.asignar_equipo(clase.id_sesion, BOLETA_3CM1, 7)
    ruta = servicios.archivos.exportar_excel(Periodo.de_mes(2026, 11), tmp_path / "noviembre.xlsx")
    libro = load_workbook(ruta)
    assert libro.sheetnames == ["Resumen", "Detalle"]
    detalle = list(libro["Detalle"].iter_rows(values_only=True))
    assert len(detalle) == 2 and BOLETA_3CM1 in detalle[1] and 7 in detalle[1]
    with pytest.raises(ArchivoInvalido):
        servicios.archivos.exportar_excel(Periodo.de_mes(2026, 11), tmp_path / "noviembre.exe")
