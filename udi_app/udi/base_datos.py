"""Conexión a SQLite, tablas, migraciones, transacciones y respaldos.

Es, junto con ``repositorio.py``, el único archivo que conoce ``sqlite3``.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, List, NamedTuple, Optional, Sequence, Tuple

from .configuracion import Configuracion
from .excepciones import ErrorRespaldo, ErrorUDI, RespaldoInvalido

ESQUEMA = """
CREATE TABLE IF NOT EXISTS maestro (
    id_maestro  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE,
    activo      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS grupo (
    clave_grupo TEXT    PRIMARY KEY,
    materia     TEXT    NOT NULL,
    id_maestro  INTEGER NOT NULL REFERENCES maestro (id_maestro),
    activo      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS alumno (
    boleta  TEXT    PRIMARY KEY,
    nombre  TEXT    NOT NULL,
    activo  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS inscripcion (
    boleta      TEXT    NOT NULL REFERENCES alumno (boleta),
    clave_grupo TEXT    NOT NULL REFERENCES grupo (clave_grupo),
    activo      INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (boleta, clave_grupo)
);

CREATE TABLE IF NOT EXISTS laboratorio (
    id_laboratorio TEXT    PRIMARY KEY,
    nombre         TEXT    NOT NULL,
    activo         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS equipo (
    id_equipo      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_laboratorio TEXT    NOT NULL REFERENCES laboratorio (id_laboratorio),
    numero         INTEGER NOT NULL,
    codigo         TEXT    NOT NULL UNIQUE,
    estado         TEXT    NOT NULL DEFAULT 'LIBRE'
                   CHECK (estado IN ('LIBRE', 'FUERA_DE_SERVICIO')),
    UNIQUE (id_laboratorio, numero)
);

CREATE TABLE IF NOT EXISTS sesion (
    id_sesion       INTEGER PRIMARY KEY AUTOINCREMENT,
    clave_grupo     TEXT    NOT NULL REFERENCES grupo (clave_grupo),
    id_laboratorio  TEXT    NOT NULL REFERENCES laboratorio (id_laboratorio),
    hora_inicio     TEXT    NOT NULL,
    hora_fin        TEXT    NOT NULL,
    estado          TEXT    NOT NULL DEFAULT 'PROGRAMADA',
    estado_maestro  TEXT    NOT NULL DEFAULT 'SIN_ANOTAR'
);

CREATE TABLE IF NOT EXISTS asistencia (
    id_asistencia INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sesion     INTEGER NOT NULL REFERENCES sesion (id_sesion),
    boleta        TEXT    NOT NULL REFERENCES alumno (boleta),
    estado        TEXT    NOT NULL,
    hora_llegada  TEXT,
    es_retardo    INTEGER NOT NULL DEFAULT 0,
    es_laptop     INTEGER NOT NULL DEFAULT 0,
    origen        TEXT    NOT NULL DEFAULT 'TABLETA',
    UNIQUE (id_sesion, boleta)
);

CREATE TABLE IF NOT EXISTS uso_equipo (
    id_uso        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_asistencia INTEGER NOT NULL REFERENCES asistencia (id_asistencia),
    id_equipo     INTEGER NOT NULL REFERENCES equipo (id_equipo),
    hora_inicio   TEXT    NOT NULL,
    hora_fin      TEXT
);

CREATE TABLE IF NOT EXISTS reporte (
    id_reporte     INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo           TEXT    NOT NULL,
    id_laboratorio TEXT    NOT NULL REFERENCES laboratorio (id_laboratorio),
    id_equipo      INTEGER REFERENCES equipo (id_equipo),
    texto          TEXT    NOT NULL,
    fecha          TEXT    NOT NULL,
    ultimo_usuario TEXT
);

CREATE TABLE IF NOT EXISTS bitacora (
    id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora  TEXT NOT NULL,
    accion      TEXT NOT NULL,
    detalle     TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_sesion_inicio     ON sesion (hora_inicio);
CREATE INDEX IF NOT EXISTS ix_asistencia_sesion ON asistencia (id_sesion);
CREATE INDEX IF NOT EXISTS ix_uso_asistencia    ON uso_equipo (id_asistencia);
CREATE INDEX IF NOT EXISTS ix_uso_equipo_activo ON uso_equipo (id_equipo, hora_fin);
"""


class Migracion(NamedTuple):
    """Un cambio a la estructura de la base, aplicado una sola vez y en orden."""

    version: int
    descripcion: str
    sentencias: Tuple[str, ...]


# Para cambiar la estructura: agregar una Migracion al final con la versión
# siguiente. Nunca editar ni borrar una que ya se entregó.
MIGRACIONES: Tuple[Migracion, ...] = ()

VERSION_ESQUEMA = max((m.version for m in MIGRACIONES), default=0)
_TABLAS_OBLIGATORIAS = frozenset({"alumno", "grupo", "sesion", "asistencia", "equipo", "bitacora"})


class BaseDatos:
    """Dueña de la conexión. Los repositorios le piden ejecutar el SQL."""

    def __init__(self, configuracion: Configuracion) -> None:
        self._configuracion = configuracion
        configuracion.crear_carpetas()
        # isolation_level=None: las transacciones se manejan a mano en transaccion().
        self._conexion = sqlite3.connect(
            configuracion.ruta_bd, isolation_level=None, check_same_thread=False
        )
        self._conexion.row_factory = sqlite3.Row
        self._conexion.execute("PRAGMA foreign_keys = ON")
        self._profundidad = 0

    # -- estructura ---------------------------------------------------------
    def crear_tablas(self) -> None:
        """Crea lo que falte y aplica las migraciones pendientes."""
        self._conexion.executescript(ESQUEMA)
        self._migrar()

    @property
    def version_esquema(self) -> int:
        return int(self._conexion.execute("PRAGMA user_version").fetchone()[0])

    def _migrar(self) -> None:
        actual = self.version_esquema
        if actual > VERSION_ESQUEMA:
            raise ErrorUDI(
                "base_mas_nueva",
                "La base de datos fue creada con una versión más nueva del programa. "
                "Actualiza la aplicación.",
            )
        for migracion in MIGRACIONES:
            if migracion.version <= actual:
                continue
            with self.transaccion():
                for sentencia in migracion.sentencias:
                    self._conexion.execute(sentencia)
                # PRAGMA no acepta parámetros; el valor es un entero propio, no un dato externo.
                self._conexion.execute(f"PRAGMA user_version = {int(migracion.version)}")

    # -- consultas ----------------------------------------------------------
    def ejecutar(self, sql: str, parametros: Sequence[Any] = ()) -> sqlite3.Cursor:
        return self._conexion.execute(sql, parametros)

    def uno(self, sql: str, parametros: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        return self._conexion.execute(sql, parametros).fetchone()

    def todos(self, sql: str, parametros: Sequence[Any] = ()) -> List[sqlite3.Row]:
        return self._conexion.execute(sql, parametros).fetchall()

    # -- transacciones ------------------------------------------------------
    @contextmanager
    def transaccion(self) -> Iterator[None]:
        """Agrupa escrituras: o se guardan todas o no se guarda ninguna.

        Se pueden anidar; solo la más externa hace COMMIT o ROLLBACK.
        """
        if self._profundidad == 0:
            self._conexion.execute("BEGIN")
        self._profundidad += 1
        try:
            yield
        except BaseException:
            self._profundidad -= 1
            if self._profundidad == 0:
                self._conexion.execute("ROLLBACK")
            raise
        else:
            self._profundidad -= 1
            if self._profundidad == 0:
                self._conexion.execute("COMMIT")

    # -- respaldos ----------------------------------------------------------
    def respaldar(self, momento: Optional[datetime] = None) -> Optional[Path]:
        """Copia la base a respaldos/ con la fecha en el nombre.

        Devuelve la ruta creada, o None si la base vive en memoria.
        """
        if self._configuracion.en_memoria:
            return None
        momento = momento or datetime.now()
        carpeta = self._configuracion.carpeta_respaldos
        destino_ruta = carpeta / f"udi_{momento:%Y%m%d_%H%M%S}.db"
        consecutivo = 1
        while destino_ruta.exists():  # dos respaldos en el mismo segundo
            destino_ruta = carpeta / f"udi_{momento:%Y%m%d_%H%M%S}_{consecutivo}.db"
            consecutivo += 1
        try:
            destino = sqlite3.connect(destino_ruta)
            try:
                self._conexion.backup(destino)
            finally:
                destino.close()
        except (sqlite3.Error, OSError) as error:
            raise ErrorRespaldo(str(error)) from error
        return destino_ruta

    def restaurar(self, ruta: Path) -> None:
        """Reemplaza TODO el contenido de la base por el del respaldo indicado."""
        if self._profundidad:
            raise RuntimeError("No se puede restaurar dentro de una transacción.")
        try:
            origen = sqlite3.connect(Path(ruta).resolve().as_uri() + "?mode=ro", uri=True)
        except sqlite3.Error as error:
            raise RespaldoInvalido("no se pudo abrir el archivo.") from error
        try:
            self._validar_respaldo(origen)
            origen.backup(self._conexion)
        except sqlite3.Error as error:
            raise RespaldoInvalido("el archivo no es una base de datos del sistema.") from error
        finally:
            origen.close()
        self._conexion.execute("PRAGMA foreign_keys = ON")
        self._migrar()  # un respaldo viejo puede traer una estructura anterior

    @staticmethod
    def _validar_respaldo(origen: sqlite3.Connection) -> None:
        if origen.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RespaldoInvalido("el archivo está dañado.")
        tablas = {
            fila[0]
            for fila in origen.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if not _TABLAS_OBLIGATORIAS <= tablas:
            raise RespaldoInvalido("el archivo no es una base de datos del sistema.")

    # -- mantenimiento ------------------------------------------------------
    def verificar_integridad(self) -> List[str]:
        """Lista de problemas encontrados; vacía si la base está sana."""
        problemas = [
            fila[0]
            for fila in self._conexion.execute("PRAGMA integrity_check")
            if fila[0] != "ok"
        ]
        for fila in self._conexion.execute("PRAGMA foreign_key_check"):
            problemas.append(f"Llave foránea rota en la tabla {fila[0]} (fila {fila[1]}).")
        return problemas

    def compactar(self) -> None:
        """Recupera el espacio que dejan las filas borradas (VACUUM)."""
        if self._profundidad:
            raise RuntimeError("No se puede compactar dentro de una transacción.")
        self._conexion.execute("VACUUM")

    @property
    def tamano_bytes(self) -> int:
        paginas = self._conexion.execute("PRAGMA page_count").fetchone()[0]
        tamano_pagina = self._conexion.execute("PRAGMA page_size").fetchone()[0]
        return int(paginas) * int(tamano_pagina)

    def cerrar(self) -> None:
        self._conexion.close()
