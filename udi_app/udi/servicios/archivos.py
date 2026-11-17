"""Importar listas y horarios desde CSV/Excel y exportar asistencia a Excel.

Para aceptar otro formato (por ejemplo ODS) basta con escribir una subclase de
``LectorTabla`` y pasarla a ``ServicioArchivos``: nada más cambia.
"""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, NamedTuple, Optional, Sequence, Set, Tuple

from ..auditoria import Auditoria
from ..base_datos import BaseDatos
from ..configuracion import Configuracion, Reloj
from ..excepciones import ArchivoInvalido
from ..modelos import Alumno, ErrorFila, Grupo, Periodo, ResumenImportacion
from ..repositorio import (
    RepositorioAlumnos,
    RepositorioAsistencias,
    RepositorioGrupos,
    RepositorioLaboratorios,
    RepositorioSesiones,
)
from ..utilidades import a_texto, a_texto_boleta, normalizar_texto
from ..validaciones import LARGO_MAXIMO_NOMBRE, es_boleta_valida, es_clave_valida
from .estadisticas import ServicioEstadisticas

Fila = List[Any]


# --------------------------------------------------------------------------- #
# Lectores: uno por tipo de archivo
# --------------------------------------------------------------------------- #
class LectorTabla(ABC):
    """Lee un archivo y devuelve (encabezados, filas). La fila 1 es el encabezado."""

    extensiones: Tuple[str, ...] = ()

    @abstractmethod
    def leer(self, ruta: Path) -> Tuple[List[str], List[Fila]]:
        ...


class LectorCSV(LectorTabla):
    extensiones = (".csv",)

    def leer(self, ruta: Path) -> Tuple[List[str], List[Fila]]:
        try:
            texto = ruta.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            texto = ruta.read_text(encoding="cp1252")  # CSV "ANSI" de Excel en Windows
        try:
            dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t|")
        except csv.Error:
            dialecto = csv.excel
        filas = [list(f) for f in csv.reader(io.StringIO(texto), dialecto)]
        if not filas:
            raise ArchivoInvalido("el archivo está vacío.")
        return [a_texto(c) for c in filas[0]], filas[1:]


class LectorExcel(LectorTabla):
    extensiones = (".xlsx", ".xlsm")

    def leer(self, ruta: Path) -> Tuple[List[str], List[Fila]]:
        try:
            from openpyxl import load_workbook  # import tardío: solo si hace falta
        except ImportError as error:
            raise ArchivoInvalido("falta instalar openpyxl (pip install openpyxl).") from error
        try:
            libro = load_workbook(ruta, read_only=True, data_only=True)
        except Exception as error:  # noqa: BLE001 - openpyxl lanza varios tipos
            raise ArchivoInvalido("no se pudo abrir el archivo de Excel.") from error
        try:
            filas = [list(f) for f in libro.active.iter_rows(values_only=True)]
        finally:
            libro.close()
        if not filas:
            raise ArchivoInvalido("el archivo está vacío.")
        return [a_texto(c) for c in filas[0]], filas[1:]


# --------------------------------------------------------------------------- #
# Columnas y valores
# --------------------------------------------------------------------------- #
def _clave(texto: str) -> str:
    return normalizar_texto(texto.replace("_", " "))


def _alias(*nombres: str) -> FrozenSet[str]:
    return frozenset(_clave(n) for n in nombres)


ALIAS_LISTA: Dict[str, FrozenSet[str]] = {
    "boleta": _alias("boleta", "no boleta", "numero de boleta", "matricula"),
    "nombre": _alias("nombre", "alumno", "nombre del alumno", "nombre completo"),
    "clave_grupo": _alias("clave_grupo", "grupo", "clave del grupo"),
    "materia": _alias("materia", "asignatura", "unidad de aprendizaje"),
    "maestro": _alias("maestro", "profesor", "docente"),
}
OBLIGATORIAS_LISTA = ("boleta", "nombre", "clave_grupo")

ALIAS_HORARIO: Dict[str, FrozenSet[str]] = {
    "fecha": _alias("fecha", "dia"),
    "hora_inicio": _alias("hora_inicio", "hora", "inicio", "hora de inicio"),
    "hora_fin": _alias("hora_fin", "fin", "hora de fin"),
    "clave_grupo": ALIAS_LISTA["clave_grupo"],
    "materia": ALIAS_LISTA["materia"],
    "maestro": ALIAS_LISTA["maestro"],
    "laboratorio": _alias("laboratorio", "lab", "udi"),
}
OBLIGATORIAS_HORARIO = ("fecha", "hora_inicio", "clave_grupo", "laboratorio")


class _Columnas:
    """Ubica cada columna por su nombre, sin importar acentos ni mayúsculas."""

    def __init__(
        self,
        encabezados: Sequence[str],
        alias: Dict[str, FrozenSet[str]],
        obligatorias: Sequence[str],
    ) -> None:
        self._posicion: Dict[str, int] = {}
        for pos, encabezado in enumerate(encabezados):
            nombre = _clave(encabezado)
            for canonica, nombres in alias.items():
                if nombre in nombres and canonica not in self._posicion:
                    self._posicion[canonica] = pos
        faltan = [c for c in obligatorias if c not in self._posicion]
        if faltan:
            raise ArchivoInvalido("faltan las columnas: " + ", ".join(faltan) + ".")

    def valor(self, fila: Fila, canonica: str) -> Any:
        pos = self._posicion.get(canonica)
        return fila[pos] if pos is not None and pos < len(fila) else None


def _fila_vacia(fila: Fila) -> bool:
    return not any(a_texto(celda) for celda in fila)


def _a_fecha(valor: Any) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = a_texto(valor)
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"fecha no válida: '{texto}'")


def _a_hora(valor: Any) -> time:
    if isinstance(valor, datetime):
        return valor.time()
    if isinstance(valor, time):
        return valor
    texto = a_texto(valor)
    for formato in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            continue
    raise ValueError(f"hora no válida: '{texto}'")


class _ClaseDelArchivo(NamedTuple):
    numero_fila: int
    clave_grupo: str
    id_laboratorio: str
    inicio: datetime
    fin: datetime


# --------------------------------------------------------------------------- #
# Servicio
# --------------------------------------------------------------------------- #
class ServicioArchivos:
    """Las importaciones son todo o nada: con un solo error no se guarda nada."""

    def __init__(
        self,
        base_datos: BaseDatos,
        configuracion: Configuracion,
        reloj: Reloj,
        alumnos: RepositorioAlumnos,
        grupos: RepositorioGrupos,
        laboratorios: RepositorioLaboratorios,
        sesiones: RepositorioSesiones,
        asistencias: RepositorioAsistencias,
        auditoria: Auditoria,
        estadisticas: ServicioEstadisticas,
        lectores: Optional[Sequence[LectorTabla]] = None,
    ) -> None:
        self._bd = base_datos
        self._configuracion = configuracion
        self._reloj = reloj
        self._alumnos = alumnos
        self._grupos = grupos
        self._laboratorios = laboratorios
        self._sesiones = sesiones
        self._asistencias = asistencias
        self._auditoria = auditoria
        self._estadisticas = estadisticas
        self._lectores: Dict[str, LectorTabla] = {}
        for lector in lectores or (LectorCSV(), LectorExcel()):
            for extension in lector.extensiones:
                self._lectores[extension] = lector

    # ------------------------------------------------------------------ #
    # Importar lista de alumnos
    # ------------------------------------------------------------------ #
    def importar_lista(self, ruta: Path) -> ResumenImportacion:
        """Columnas: boleta, nombre, clave_grupo (y opcionales materia, maestro).

        Si el grupo todavía no existe, el archivo debe traer materia y maestro
        para crearlo.
        """
        columnas, filas = self._leer(Path(ruta), ALIAS_LISTA, OBLIGATORIAS_LISTA)
        errores: List[ErrorFila] = []
        registros: List[Tuple[int, str, str, str]] = []
        definidos: Dict[str, Grupo] = {}

        for numero, fila in enumerate(filas, start=2):
            if _fila_vacia(fila):
                continue
            boleta = a_texto_boleta(columnas.valor(fila, "boleta"))
            nombre = a_texto(columnas.valor(fila, "nombre"))
            clave = a_texto(columnas.valor(fila, "clave_grupo"))
            materia = a_texto(columnas.valor(fila, "materia"))
            maestro = a_texto(columnas.valor(fila, "maestro"))
            faltan = [
                etiqueta
                for etiqueta, valor in (("boleta", boleta), ("nombre", nombre), ("clave_grupo", clave))
                if not valor
            ]
            if faltan:
                errores.append(ErrorFila(numero, "Falta: " + ", ".join(faltan) + "."))
                continue
            motivo = self._motivo_alumno_invalido(boleta, nombre, clave)
            if motivo:
                errores.append(ErrorFila(numero, motivo))
                continue
            if materia and maestro:
                definidos[clave] = Grupo(clave, materia, maestro)
            registros.append((numero, boleta, nombre, clave))

        for numero, _, _, clave in registros:
            if clave not in definidos and self._grupos.buscar(clave) is None:
                errores.append(
                    ErrorFila(
                        numero,
                        f"El grupo {clave} no existe. Agrega las columnas materia y maestro.",
                    )
                )
        if errores:
            return self._con_errores(errores)

        agregados = actualizados = 0
        vistos: Set[str] = set()
        with self._bd.transaccion():
            for grupo in definidos.values():
                self._grupos.guardar(grupo)
            for _, boleta, nombre, clave in registros:
                era_nuevo = self._alumnos.guardar(Alumno(boleta, nombre, clave))
                if boleta not in vistos:
                    vistos.add(boleta)
                    agregados += int(era_nuevo)
                    actualizados += int(not era_nuevo)
                self._alumnos.inscribir(boleta, clave)
            self._anotar(
                "IMPORTAR_LISTA",
                f"archivo={Path(ruta).name} agregados={agregados} actualizados={actualizados}",
            )
        return ResumenImportacion(agregados, actualizados)

    # ------------------------------------------------------------------ #
    # Importar horario
    # ------------------------------------------------------------------ #
    def importar_horario(self, ruta: Path) -> ResumenImportacion:
        """Columnas: fecha, hora_inicio, clave_grupo, laboratorio (opcionales hora_fin, materia, maestro)."""
        columnas, filas = self._leer(Path(ruta), ALIAS_HORARIO, OBLIGATORIAS_HORARIO)
        errores: List[ErrorFila] = []
        definidos: Dict[str, Grupo] = {}
        candidatas: List[_ClaseDelArchivo] = []

        for numero, fila in enumerate(filas, start=2):
            if _fila_vacia(fila):
                continue
            try:
                clase = self._clase_de_fila(numero, fila, columnas, definidos)
            except ValueError as error:
                errores.append(ErrorFila(numero, str(error)))
                continue
            candidatas.append(clase)

        nuevas: List[_ClaseDelArchivo] = []
        actualizadas = 0
        conocidas: Set[Tuple[str, str, datetime]] = set()
        for clase in candidatas:
            motivo = self._motivo_invalido(clase, definidos)
            if motivo:
                errores.append(ErrorFila(clase.numero_fila, motivo))
                continue
            exacta = (clase.clave_grupo, clase.id_laboratorio, clase.inicio)
            if exacta in conocidas or self._sesiones.buscar_exacta(*exacta):
                conocidas.add(exacta)
                actualizadas += 1
                continue
            choque = self._sesiones.buscar_empalme(clase.id_laboratorio, clase.inicio, clase.fin)
            if choque is not None:
                errores.append(
                    ErrorFila(
                        clase.numero_fila,
                        f"Se empalma con {choque.grupo.materia} ({choque.grupo.clave_grupo}) "
                        f"en {clase.id_laboratorio}.",
                    )
                )
                continue
            otra = next(
                (
                    n
                    for n in nuevas
                    if n.id_laboratorio == clase.id_laboratorio
                    and clase.inicio < n.fin
                    and clase.fin > n.inicio
                ),
                None,
            )
            if otra is not None:
                errores.append(
                    ErrorFila(clase.numero_fila, f"Se empalma con la fila {otra.numero_fila}.")
                )
                continue
            conocidas.add(exacta)
            nuevas.append(clase)

        if errores:
            return self._con_errores(errores)

        with self._bd.transaccion():
            for grupo in definidos.values():
                self._grupos.guardar(grupo)
            for clase in nuevas:
                self._sesiones.crear(
                    clase.clave_grupo, clase.id_laboratorio, clase.inicio, clase.fin
                )
            self._anotar("IMPORTAR_HORARIO", f"agregados={len(nuevas)} existentes={actualizadas}")
        return ResumenImportacion(len(nuevas), actualizadas)

    # ------------------------------------------------------------------ #
    # Exportar
    # ------------------------------------------------------------------ #
    def exportar_excel(self, periodo: Periodo, ruta: Optional[Path] = None) -> Path:
        """Libro con hoja "Resumen" (por materia) y hoja "Detalle" (alumno por alumno)."""
        try:
            from openpyxl import Workbook
        except ImportError as error:
            raise ArchivoInvalido("falta instalar openpyxl (pip install openpyxl).") from error

        destino = Path(ruta) if ruta else (
            self._configuracion.carpeta_exportaciones
            / f"asistencia_{periodo.desde:%Y%m%d}_{periodo.hasta:%Y%m%d}.xlsx"
        )
        if destino.suffix.lower() != ".xlsx":
            raise ArchivoInvalido("el archivo de salida debe terminar en .xlsx.")
        destino.parent.mkdir(parents=True, exist_ok=True)

        libro = Workbook()
        resumen = libro.active
        resumen.title = "Resumen"
        resumen.append(["Materia", "Maestros", "Grupos", "Grupos que vinieron", "Alumnos"])
        for fila in self._estadisticas.resumen_por_materia(periodo):
            resumen.append(
                [fila.materia, fila.maestros, fila.grupos, fila.grupos_que_vinieron, fila.alumnos]
            )

        detalle = libro.create_sheet("Detalle")
        detalle.append(
            [
                "Fecha", "Hora", "Laboratorio", "Grupo", "Materia", "Maestro", "Estado maestro",
                "Boleta", "Alumno", "Estado", "Llegada", "Retardo", "Computadora", "Laptop", "Origen",
            ]
        )
        for sesion in self._sesiones.listar_periodo(periodo):
            for a in self._asistencias.listar_por_sesion(sesion.id_sesion):
                detalle.append(
                    [
                        sesion.hora_inicio.date().isoformat(),
                        f"{sesion.hora_inicio:%H:%M}",
                        sesion.id_laboratorio,
                        sesion.grupo.clave_grupo,
                        sesion.grupo.materia,
                        sesion.grupo.maestro,
                        sesion.estado_maestro.value,
                        a.alumno.boleta,
                        a.alumno.nombre,
                        a.estado.value,
                        f"{a.hora_llegada:%H:%M:%S}" if a.hora_llegada else "",
                        "Sí" if a.es_retardo else "No",
                        a.numero_equipo if a.numero_equipo is not None else "",
                        "Sí" if a.es_laptop else "No",
                        a.origen.value,
                    ]
                )
        for hoja in (resumen, detalle):
            self._ajustar_columnas(hoja)
        libro.save(destino)
        return destino

    # ------------------------------------------------------------------ #
    # Apoyo interno
    # ------------------------------------------------------------------ #
    def _leer(
        self,
        ruta: Path,
        alias: Dict[str, FrozenSet[str]],
        obligatorias: Sequence[str],
    ) -> Tuple[_Columnas, List[Fila]]:
        if not ruta.is_file():
            raise ArchivoInvalido("no se encontró el archivo.")
        megas = self._configuracion.max_megas_archivo
        if ruta.stat().st_size > megas * 1024 * 1024:
            raise ArchivoInvalido(f"el archivo pesa más de {megas} MB.")
        lector = self._lectores.get(ruta.suffix.lower())
        if lector is None:
            tipos = ", ".join(sorted(self._lectores))
            raise ArchivoInvalido(f"formato no soportado ({ruta.suffix or 'sin extensión'}). Usa {tipos}.")
        encabezados, filas = lector.leer(ruta)
        if len(filas) > self._configuracion.max_filas_archivo:
            raise ArchivoInvalido(
                f"el archivo tiene más de {self._configuracion.max_filas_archivo} filas."
            )
        return _Columnas(encabezados, alias, obligatorias), filas

    def _clase_de_fila(
        self,
        numero: int,
        fila: Fila,
        columnas: _Columnas,
        definidos: Dict[str, Grupo],
    ) -> _ClaseDelArchivo:
        clave = a_texto(columnas.valor(fila, "clave_grupo"))
        laboratorio = a_texto(columnas.valor(fila, "laboratorio"))
        if not clave or not laboratorio:
            raise ValueError("Falta: clave_grupo o laboratorio.")
        if not es_clave_valida(clave) or not es_clave_valida(laboratorio):
            raise ValueError("El grupo o el laboratorio tienen caracteres no permitidos.")
        fecha = _a_fecha(columnas.valor(fila, "fecha"))
        hora_inicio = _a_hora(columnas.valor(fila, "hora_inicio"))
        inicio = datetime.combine(fecha, hora_inicio)
        valor_fin = columnas.valor(fila, "hora_fin")
        if a_texto(valor_fin):
            fin = datetime.combine(fecha, _a_hora(valor_fin))
        else:
            fin = inicio + timedelta(minutes=self._configuracion.minutos_clase)
        if fin <= inicio:
            raise ValueError("La clase debe terminar después de empezar.")
        materia = a_texto(columnas.valor(fila, "materia"))
        maestro = a_texto(columnas.valor(fila, "maestro"))
        if materia and maestro:
            definidos[clave] = Grupo(clave, materia, maestro)
        return _ClaseDelArchivo(numero, clave, laboratorio, inicio, fin)

    def _motivo_invalido(self, clase: _ClaseDelArchivo, definidos: Dict[str, Grupo]) -> Optional[str]:
        if clase.clave_grupo not in definidos and self._grupos.buscar(clase.clave_grupo) is None:
            return f"El grupo {clase.clave_grupo} no existe. Agrega las columnas materia y maestro."
        if self._laboratorios.buscar(clase.id_laboratorio) is None:
            return f"El laboratorio {clase.id_laboratorio} no existe."
        return None

    @staticmethod
    def _motivo_alumno_invalido(boleta: str, nombre: str, clave: str) -> Optional[str]:
        if not es_boleta_valida(boleta):
            return "La boleta no es válida."
        if len(nombre) > LARGO_MAXIMO_NOMBRE:
            return f"El nombre pasa de {LARGO_MAXIMO_NOMBRE} caracteres."
        if not es_clave_valida(clave):
            return "La clave del grupo tiene caracteres no permitidos."
        return None

    @staticmethod
    def _con_errores(errores: List[ErrorFila]) -> ResumenImportacion:
        return ResumenImportacion(0, 0, tuple(sorted(errores, key=lambda e: e.numero_fila)))

    @staticmethod
    def _ajustar_columnas(hoja: Any) -> None:
        for columna in hoja.columns:
            ancho = max((len(str(c.value)) for c in columna if c.value is not None), default=8)
            hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 2, 45)

    def _anotar(self, accion: str, detalle: str) -> None:
        self._auditoria.anotar(accion, detalle)
