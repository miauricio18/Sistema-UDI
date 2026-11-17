"""Todo el SQL del sistema, una clase por tabla (o grupo de tablas muy ligadas).

Reglas de esta capa:
* Recibe y devuelve modelos, nunca filas de SQLite.
* No decide nada de negocio: solo guarda y consulta.
* Quien escribe es responsable de abrir ``BaseDatos.transaccion()``.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Dict, List, Optional

from .base_datos import BaseDatos
from .modelos import (
    Alumno,
    Asistencia,
    EstadoAsistencia,
    EstadoEquipo,
    EstadoMaestro,
    EstadoSesion,
    Equipo,
    FilaEstadistica,
    DiaAsistencia,
    Grupo,
    Laboratorio,
    Origen,
    Periodo,
    RegistroBitacora,
    Reporte,
    Sesion,
    TipoReporte,
)

ESTADOS_CON_LLEGADA = (EstadoAsistencia.LLEGO.value, EstadoAsistencia.RETARDO.value)


# --------------------------------------------------------------------------- #
# Conversión de fechas y filas
# --------------------------------------------------------------------------- #
def _a_texto(momento: datetime) -> str:
    return momento.isoformat(timespec="seconds")


def _a_fecha_hora(texto: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(texto) if texto else None


def _grupo_de(fila: sqlite3.Row) -> Grupo:
    return Grupo(fila["clave_grupo"], fila["materia"], fila["maestro"])


def _sesion_de(fila: sqlite3.Row) -> Sesion:
    return Sesion(
        id_sesion=fila["id_sesion"],
        grupo=_grupo_de(fila),
        id_laboratorio=fila["id_laboratorio"],
        hora_inicio=datetime.fromisoformat(fila["hora_inicio"]),
        hora_fin=datetime.fromisoformat(fila["hora_fin"]),
        estado=EstadoSesion(fila["estado"]),
        estado_maestro=EstadoMaestro(fila["estado_maestro"]),
    )


def _equipo_de(fila: sqlite3.Row) -> Equipo:
    return Equipo(
        id_equipo=fila["id_equipo"],
        id_laboratorio=fila["id_laboratorio"],
        numero=fila["numero"],
        estado=EstadoEquipo(fila["estado"]),
        codigo=fila["codigo"],
    )


def _asistencia_de(fila: sqlite3.Row) -> Asistencia:
    return Asistencia(
        alumno=Alumno(fila["boleta"], fila["nombre"], fila["clave_grupo"]),
        estado=EstadoAsistencia(fila["estado"]),
        hora_llegada=_a_fecha_hora(fila["hora_llegada"]),
        es_retardo=bool(fila["es_retardo"]),
        numero_equipo=fila["numero_equipo"],
        es_laptop=bool(fila["es_laptop"]),
        origen=Origen(fila["origen"]),
    )


class _RepositorioBase:
    def __init__(self, base_datos: BaseDatos) -> None:
        self._bd = base_datos


# --------------------------------------------------------------------------- #
# Alumnos e inscripciones
# --------------------------------------------------------------------------- #
class RepositorioAlumnos(_RepositorioBase):
    def buscar(self, boleta: str) -> Optional[Alumno]:
        """Busca un alumno activo. Su grupo es el primero en el que está inscrito."""
        fila = self._bd.uno(
            """
            SELECT a.boleta, a.nombre,
                   COALESCE((SELECT i.clave_grupo FROM inscripcion i
                              WHERE i.boleta = a.boleta AND i.activo = 1
                              ORDER BY i.clave_grupo LIMIT 1), '') AS clave_grupo
              FROM alumno a
             WHERE a.boleta = ? AND a.activo = 1
            """,
            (boleta,),
        )
        return Alumno(fila["boleta"], fila["nombre"], fila["clave_grupo"]) if fila else None

    def contar(self) -> int:
        return int(self._bd.uno("SELECT COUNT(*) FROM alumno WHERE activo = 1")[0])

    def listar_por_grupo(self, clave_grupo: str) -> List[Alumno]:
        filas = self._bd.todos(
            """
            SELECT a.boleta, a.nombre, i.clave_grupo
              FROM inscripcion i
              JOIN alumno a ON a.boleta = i.boleta
             WHERE i.clave_grupo = ? AND i.activo = 1 AND a.activo = 1
             ORDER BY a.nombre
            """,
            (clave_grupo,),
        )
        return [Alumno(f["boleta"], f["nombre"], f["clave_grupo"]) for f in filas]

    def esta_inscrito(self, boleta: str, clave_grupo: str) -> bool:
        fila = self._bd.uno(
            "SELECT 1 FROM inscripcion WHERE boleta = ? AND clave_grupo = ? AND activo = 1",
            (boleta, clave_grupo),
        )
        return fila is not None

    def grupos_de(self, boleta: str) -> List[str]:
        filas = self._bd.todos(
            "SELECT clave_grupo FROM inscripcion WHERE boleta = ? AND activo = 1 ORDER BY clave_grupo",
            (boleta,),
        )
        return [f["clave_grupo"] for f in filas]

    def guardar(self, alumno: Alumno) -> bool:
        """Crea o actualiza al alumno. Devuelve True si era nuevo."""
        existente = self._bd.uno("SELECT 1 FROM alumno WHERE boleta = ?", (alumno.boleta,))
        self._bd.ejecutar(
            """
            INSERT INTO alumno (boleta, nombre, activo) VALUES (?, ?, 1)
            ON CONFLICT (boleta) DO UPDATE SET nombre = excluded.nombre, activo = 1
            """,
            (alumno.boleta, alumno.nombre),
        )
        return existente is None

    def inscribir(self, boleta: str, clave_grupo: str) -> None:
        self._bd.ejecutar(
            """
            INSERT INTO inscripcion (boleta, clave_grupo, activo) VALUES (?, ?, 1)
            ON CONFLICT (boleta, clave_grupo) DO UPDATE SET activo = 1
            """,
            (boleta, clave_grupo),
        )


# --------------------------------------------------------------------------- #
# Grupos (con su maestro) y laboratorios
# --------------------------------------------------------------------------- #
class RepositorioGrupos(_RepositorioBase):
    _SELECT = """
        SELECT g.clave_grupo, g.materia, m.nombre AS maestro
          FROM grupo g
          JOIN maestro m ON m.id_maestro = g.id_maestro
    """

    def buscar(self, clave_grupo: str) -> Optional[Grupo]:
        fila = self._bd.uno(self._SELECT + " WHERE g.clave_grupo = ? AND g.activo = 1", (clave_grupo,))
        return _grupo_de(fila) if fila else None

    def listar(self) -> List[Grupo]:
        filas = self._bd.todos(self._SELECT + " WHERE g.activo = 1 ORDER BY g.clave_grupo")
        return [_grupo_de(f) for f in filas]

    def guardar(self, grupo: Grupo) -> bool:
        """Crea o actualiza el grupo (y su maestro). Devuelve True si era nuevo."""
        existente = self._bd.uno("SELECT 1 FROM grupo WHERE clave_grupo = ?", (grupo.clave_grupo,))
        self._bd.ejecutar(
            "INSERT INTO maestro (nombre) VALUES (?) ON CONFLICT (nombre) DO UPDATE SET activo = 1",
            (grupo.maestro,),
        )
        id_maestro = self._bd.uno(
            "SELECT id_maestro FROM maestro WHERE nombre = ?", (grupo.maestro,)
        )["id_maestro"]
        self._bd.ejecutar(
            """
            INSERT INTO grupo (clave_grupo, materia, id_maestro, activo) VALUES (?, ?, ?, 1)
            ON CONFLICT (clave_grupo) DO UPDATE
               SET materia = excluded.materia, id_maestro = excluded.id_maestro, activo = 1
            """,
            (grupo.clave_grupo, grupo.materia, id_maestro),
        )
        return existente is None


class RepositorioLaboratorios(_RepositorioBase):
    def buscar(self, id_laboratorio: str) -> Optional[Laboratorio]:
        fila = self._bd.uno(
            "SELECT id_laboratorio, nombre FROM laboratorio WHERE id_laboratorio = ? AND activo = 1",
            (id_laboratorio,),
        )
        return Laboratorio(fila["id_laboratorio"], fila["nombre"]) if fila else None

    def listar(self) -> List[Laboratorio]:
        filas = self._bd.todos(
            "SELECT id_laboratorio, nombre FROM laboratorio WHERE activo = 1 ORDER BY id_laboratorio"
        )
        return [Laboratorio(f["id_laboratorio"], f["nombre"]) for f in filas]

    def guardar(self, laboratorio: Laboratorio) -> bool:
        existente = self._bd.uno(
            "SELECT 1 FROM laboratorio WHERE id_laboratorio = ?", (laboratorio.id_laboratorio,)
        )
        self._bd.ejecutar(
            """
            INSERT INTO laboratorio (id_laboratorio, nombre, activo) VALUES (?, ?, 1)
            ON CONFLICT (id_laboratorio) DO UPDATE SET nombre = excluded.nombre, activo = 1
            """,
            (laboratorio.id_laboratorio, laboratorio.nombre),
        )
        return existente is None


# --------------------------------------------------------------------------- #
# Sesiones (clases)
# --------------------------------------------------------------------------- #
class RepositorioSesiones(_RepositorioBase):
    _SELECT = """
        SELECT s.id_sesion, s.id_laboratorio, s.hora_inicio, s.hora_fin, s.estado,
               s.estado_maestro, g.clave_grupo, g.materia, m.nombre AS maestro
          FROM sesion s
          JOIN grupo g   ON g.clave_grupo = s.clave_grupo
          JOIN maestro m ON m.id_maestro = g.id_maestro
    """

    def buscar(self, id_sesion: int) -> Optional[Sesion]:
        fila = self._bd.uno(self._SELECT + " WHERE s.id_sesion = ?", (id_sesion,))
        return _sesion_de(fila) if fila else None

    def contar(self) -> int:
        return int(self._bd.uno("SELECT COUNT(*) FROM sesion WHERE estado != 'CANCELADA'")[0])

    def listar_del_dia(self, dia: date) -> List[Sesion]:
        """Clases del día sin contar las canceladas, de la más temprana a la más tarde."""
        filas = self._bd.todos(
            self._SELECT
            + " WHERE date(s.hora_inicio) = ? AND s.estado != 'CANCELADA' ORDER BY s.hora_inicio, s.id_sesion",
            (dia.isoformat(),),
        )
        return [_sesion_de(f) for f in filas]

    def listar_periodo(self, periodo: Periodo) -> List[Sesion]:
        """Clases (sin canceladas) de un periodo, en orden cronológico."""
        filas = self._bd.todos(
            self._SELECT
            + """
             WHERE date(s.hora_inicio) BETWEEN ? AND ? AND s.estado != 'CANCELADA'
             ORDER BY s.hora_inicio, s.id_sesion
            """,
            (periodo.desde.isoformat(), periodo.hasta.isoformat()),
        )
        return [_sesion_de(f) for f in filas]

    def buscar_exacta(
        self, clave_grupo: str, id_laboratorio: str, hora_inicio: datetime
    ) -> Optional[Sesion]:
        fila = self._bd.uno(
            self._SELECT
            + " WHERE s.clave_grupo = ? AND s.id_laboratorio = ? AND s.hora_inicio = ? AND s.estado != 'CANCELADA'",
            (clave_grupo, id_laboratorio, _a_texto(hora_inicio)),
        )
        return _sesion_de(fila) if fila else None

    def buscar_empalme(
        self,
        id_laboratorio: str,
        hora_inicio: datetime,
        hora_fin: datetime,
        ignorar_id_sesion: Optional[int] = None,
    ) -> Optional[Sesion]:
        """Devuelve una clase del laboratorio que se cruce con ese horario, si hay."""
        fila = self._bd.uno(
            self._SELECT
            + """
             WHERE s.id_laboratorio = ? AND s.estado != 'CANCELADA'
               AND s.hora_inicio < ? AND s.hora_fin > ?
               AND s.id_sesion != ?
             LIMIT 1
            """,
            (id_laboratorio, _a_texto(hora_fin), _a_texto(hora_inicio), ignorar_id_sesion or 0),
        )
        return _sesion_de(fila) if fila else None

    def crear(
        self, clave_grupo: str, id_laboratorio: str, hora_inicio: datetime, hora_fin: datetime
    ) -> int:
        cursor = self._bd.ejecutar(
            """
            INSERT INTO sesion (clave_grupo, id_laboratorio, hora_inicio, hora_fin)
            VALUES (?, ?, ?, ?)
            """,
            (clave_grupo, id_laboratorio, _a_texto(hora_inicio), _a_texto(hora_fin)),
        )
        return int(cursor.lastrowid)

    def actualizar_clase(
        self,
        id_sesion: int,
        clave_grupo: str,
        id_laboratorio: str,
        hora_inicio: datetime,
        hora_fin: datetime,
    ) -> None:
        self._bd.ejecutar(
            """
            UPDATE sesion
               SET clave_grupo = ?, id_laboratorio = ?, hora_inicio = ?, hora_fin = ?
             WHERE id_sesion = ?
            """,
            (clave_grupo, id_laboratorio, _a_texto(hora_inicio), _a_texto(hora_fin), id_sesion),
        )

    def cambiar_estado(self, id_sesion: int, estado: EstadoSesion) -> None:
        self._bd.ejecutar(
            "UPDATE sesion SET estado = ? WHERE id_sesion = ?", (estado.value, id_sesion)
        )

    def cambiar_estado_maestro(self, id_sesion: int, estado: EstadoMaestro) -> None:
        self._bd.ejecutar(
            "UPDATE sesion SET estado_maestro = ? WHERE id_sesion = ?",
            (estado.value, id_sesion),
        )


# --------------------------------------------------------------------------- #
# Equipos y su uso
# --------------------------------------------------------------------------- #
class RepositorioEquipos(_RepositorioBase):
    """El estado guardado solo puede ser LIBRE o FUERA_DE_SERVICIO.

    OCUPADO depende de la clase y se calcula al armar el mapa.
    """

    def buscar(self, id_laboratorio: str, numero: int) -> Optional[Equipo]:
        fila = self._bd.uno(
            "SELECT * FROM equipo WHERE id_laboratorio = ? AND numero = ?",
            (id_laboratorio, numero),
        )
        return _equipo_de(fila) if fila else None

    def buscar_por_codigo(self, codigo: str) -> Optional[Equipo]:
        fila = self._bd.uno("SELECT * FROM equipo WHERE codigo = ?", (codigo,))
        return _equipo_de(fila) if fila else None

    def listar_laboratorio(self, id_laboratorio: str) -> List[Equipo]:
        filas = self._bd.todos(
            "SELECT * FROM equipo WHERE id_laboratorio = ? ORDER BY numero", (id_laboratorio,)
        )
        return [_equipo_de(f) for f in filas]

    def crear(self, id_laboratorio: str, numero: int, codigo: str) -> None:
        self._bd.ejecutar(
            "INSERT OR IGNORE INTO equipo (id_laboratorio, numero, codigo) VALUES (?, ?, ?)",
            (id_laboratorio, numero, codigo),
        )

    def cambiar_estado(self, id_equipo: int, estado: EstadoEquipo) -> None:
        if estado is EstadoEquipo.OCUPADO:
            raise ValueError("OCUPADO no se guarda: depende de la clase.")
        self._bd.ejecutar(
            "UPDATE equipo SET estado = ? WHERE id_equipo = ?", (estado.value, id_equipo)
        )


class RepositorioUsos(_RepositorioBase):
    """Quién usa cada computadora y desde cuándo (tabla uso_equipo)."""

    _OCUPANTES = """
        SELECT u.id_equipo, al.boleta, al.nombre, s.clave_grupo
          FROM uso_equipo u
          JOIN asistencia a ON a.id_asistencia = u.id_asistencia
          JOIN alumno al    ON al.boleta = a.boleta
          JOIN sesion s     ON s.id_sesion = a.id_sesion
         WHERE a.id_sesion = ? AND u.hora_fin IS NULL
    """

    def abrir(self, id_asistencia: int, id_equipo: int, ahora: datetime) -> None:
        self._bd.ejecutar(
            "INSERT INTO uso_equipo (id_asistencia, id_equipo, hora_inicio) VALUES (?, ?, ?)",
            (id_asistencia, id_equipo, _a_texto(ahora)),
        )

    def cerrar_de_asistencia(self, id_asistencia: int, ahora: datetime) -> None:
        self._bd.ejecutar(
            "UPDATE uso_equipo SET hora_fin = ? WHERE id_asistencia = ? AND hora_fin IS NULL",
            (_a_texto(ahora), id_asistencia),
        )

    def cerrar_abiertos_de_equipo(self, id_equipo: int, ahora: datetime) -> None:
        """Libera el equipo en todas las clases que todavía no se cierran."""
        self._bd.ejecutar(
            """
            UPDATE uso_equipo SET hora_fin = ?
             WHERE id_equipo = ? AND hora_fin IS NULL
               AND id_asistencia IN (
                    SELECT a.id_asistencia FROM asistencia a
                      JOIN sesion s ON s.id_sesion = a.id_sesion
                     WHERE s.estado != 'CERRADA')
            """,
            (_a_texto(ahora), id_equipo),
        )

    def ocupante(self, id_sesion: int, id_equipo: int) -> Optional[Alumno]:
        fila = self._bd.uno(self._OCUPANTES + " AND u.id_equipo = ?", (id_sesion, id_equipo))
        return Alumno(fila["boleta"], fila["nombre"], fila["clave_grupo"]) if fila else None

    def ocupantes_de_sesion(self, id_sesion: int) -> Dict[int, Alumno]:
        filas = self._bd.todos(self._OCUPANTES, (id_sesion,))
        return {
            f["id_equipo"]: Alumno(f["boleta"], f["nombre"], f["clave_grupo"]) for f in filas
        }

    def ultimo_usuario(self, id_equipo: int) -> Optional[str]:
        fila = self._bd.uno(
            """
            SELECT al.nombre
              FROM uso_equipo u
              JOIN asistencia a ON a.id_asistencia = u.id_asistencia
              JOIN alumno al    ON al.boleta = a.boleta
             WHERE u.id_equipo = ?
             ORDER BY u.hora_inicio DESC, u.id_uso DESC
             LIMIT 1
            """,
            (id_equipo,),
        )
        return fila["nombre"] if fila else None


# --------------------------------------------------------------------------- #
# Asistencias
# --------------------------------------------------------------------------- #
class RepositorioAsistencias(_RepositorioBase):
    _SELECT = """
        SELECT a.id_asistencia, a.estado, a.hora_llegada, a.es_retardo, a.es_laptop,
               a.origen, al.boleta, al.nombre, s.clave_grupo, e.numero AS numero_equipo
          FROM asistencia a
          JOIN alumno al ON al.boleta = a.boleta
          JOIN sesion s  ON s.id_sesion = a.id_sesion
          LEFT JOIN uso_equipo u ON u.id_asistencia = a.id_asistencia AND u.hora_fin IS NULL
          LEFT JOIN equipo e     ON e.id_equipo = u.id_equipo
    """

    def buscar(self, id_sesion: int, boleta: str) -> Optional[Asistencia]:
        fila = self._bd.uno(
            self._SELECT + " WHERE a.id_sesion = ? AND a.boleta = ?", (id_sesion, boleta)
        )
        return _asistencia_de(fila) if fila else None

    def listar_por_sesion(self, id_sesion: int) -> List[Asistencia]:
        filas = self._bd.todos(
            self._SELECT + " WHERE a.id_sesion = ? ORDER BY al.nombre", (id_sesion,)
        )
        return [_asistencia_de(f) for f in filas]

    def id_de(self, id_sesion: int, boleta: str) -> Optional[int]:
        fila = self._bd.uno(
            "SELECT id_asistencia FROM asistencia WHERE id_sesion = ? AND boleta = ?",
            (id_sesion, boleta),
        )
        return fila["id_asistencia"] if fila else None

    def guardar(self, id_sesion: int, asistencia: Asistencia) -> int:
        """Crea o actualiza la asistencia del alumno en esa clase. Devuelve su id."""
        self._bd.ejecutar(
            """
            INSERT INTO asistencia
                   (id_sesion, boleta, estado, hora_llegada, es_retardo, es_laptop, origen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id_sesion, boleta) DO UPDATE SET
                   estado = excluded.estado,
                   hora_llegada = excluded.hora_llegada,
                   es_retardo = excluded.es_retardo,
                   es_laptop = excluded.es_laptop,
                   origen = excluded.origen
            """,
            (
                id_sesion,
                asistencia.alumno.boleta,
                asistencia.estado.value,
                _a_texto(asistencia.hora_llegada) if asistencia.hora_llegada else None,
                int(asistencia.es_retardo),
                int(asistencia.es_laptop),
                asistencia.origen.value,
            ),
        )
        return int(self.id_de(id_sesion, asistencia.alumno.boleta))

    def marcar_laptop(self, id_asistencia: int, es_laptop: bool) -> None:
        self._bd.ejecutar(
            "UPDATE asistencia SET es_laptop = ? WHERE id_asistencia = ?",
            (int(es_laptop), id_asistencia),
        )

    def eliminar_faltas(self, id_sesion: int) -> None:
        """Se usa al reabrir un pase de lista: las faltas vuelven a ser pendientes."""
        self._bd.ejecutar(
            "DELETE FROM asistencia WHERE id_sesion = ? AND estado = ?",
            (id_sesion, EstadoAsistencia.FALTA.value),
        )

    # -- consultas para estadísticas ----------------------------------------
    def resumen_por_materia(self, periodo: Periodo) -> List[FilaEstadistica]:
        """Una fila por materia. Cuenta como asistente quien llegó o llegó con retardo."""
        filas = self._bd.todos(
            """
            SELECT g.materia,
                   COUNT(DISTINCT m.id_maestro) AS maestros,
                   COUNT(DISTINCT s.clave_grupo) AS grupos,
                   COUNT(DISTINCT CASE WHEN a.estado IN (?, ?) THEN s.clave_grupo END)
                        AS grupos_que_vinieron,
                   COUNT(DISTINCT CASE WHEN a.estado IN (?, ?) THEN a.boleta END) AS alumnos
              FROM sesion s
              JOIN grupo g   ON g.clave_grupo = s.clave_grupo
              JOIN maestro m ON m.id_maestro = g.id_maestro
              LEFT JOIN asistencia a ON a.id_sesion = s.id_sesion
             WHERE date(s.hora_inicio) BETWEEN ? AND ? AND s.estado != 'CANCELADA'
             GROUP BY g.materia
             ORDER BY g.materia
            """,
            (
                *ESTADOS_CON_LLEGADA,
                *ESTADOS_CON_LLEGADA,
                periodo.desde.isoformat(),
                periodo.hasta.isoformat(),
            ),
        )
        return [
            FilaEstadistica(
                f["materia"], f["maestros"], f["grupos"], f["grupos_que_vinieron"], f["alumnos"]
            )
            for f in filas
        ]

    def conteo_por_dia(self, clave_grupo: str, periodo: Periodo) -> List[DiaAsistencia]:
        filas = self._bd.todos(
            """
            SELECT date(s.hora_inicio) AS fecha,
                   COUNT(DISTINCT CASE WHEN a.estado IN (?, ?) THEN a.boleta END) AS asistieron,
                   (SELECT COUNT(*) FROM inscripcion i
                     WHERE i.clave_grupo = ? AND i.activo = 1) AS total
              FROM sesion s
              LEFT JOIN asistencia a ON a.id_sesion = s.id_sesion
             WHERE s.clave_grupo = ? AND s.estado != 'CANCELADA'
               AND date(s.hora_inicio) BETWEEN ? AND ?
             GROUP BY date(s.hora_inicio)
             ORDER BY fecha
            """,
            (
                *ESTADOS_CON_LLEGADA,
                clave_grupo,
                clave_grupo,
                periodo.desde.isoformat(),
                periodo.hasta.isoformat(),
            ),
        )
        return [
            DiaAsistencia(date.fromisoformat(f["fecha"]), f["asistieron"], f["total"])
            for f in filas
        ]


# --------------------------------------------------------------------------- #
# Reportes y bitácora
# --------------------------------------------------------------------------- #
class RepositorioReportes(_RepositorioBase):
    _SELECT = """
        SELECT r.id_reporte, r.tipo, r.id_laboratorio, r.texto, r.fecha,
               r.ultimo_usuario, e.numero AS numero_equipo
          FROM reporte r
          LEFT JOIN equipo e ON e.id_equipo = r.id_equipo
    """

    def guardar(
        self,
        tipo: TipoReporte,
        id_laboratorio: str,
        id_equipo: Optional[int],
        texto: str,
        fecha: datetime,
        ultimo_usuario: Optional[str],
    ) -> Reporte:
        cursor = self._bd.ejecutar(
            """
            INSERT INTO reporte (tipo, id_laboratorio, id_equipo, texto, fecha, ultimo_usuario)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tipo.value, id_laboratorio, id_equipo, texto, _a_texto(fecha), ultimo_usuario),
        )
        fila = self._bd.uno(self._SELECT + " WHERE r.id_reporte = ?", (cursor.lastrowid,))
        return self._reporte_de(fila)

    def listar(self) -> List[Reporte]:
        """Del más nuevo al más viejo."""
        filas = self._bd.todos(self._SELECT + " ORDER BY r.fecha DESC, r.id_reporte DESC")
        return [self._reporte_de(f) for f in filas]

    @staticmethod
    def _reporte_de(fila: sqlite3.Row) -> Reporte:
        return Reporte(
            id_reporte=fila["id_reporte"],
            tipo=TipoReporte(fila["tipo"]),
            id_laboratorio=fila["id_laboratorio"],
            numero_equipo=fila["numero_equipo"],
            texto=fila["texto"],
            fecha=datetime.fromisoformat(fila["fecha"]),
            ultimo_usuario=fila["ultimo_usuario"],
        )


class RepositorioBitacora(_RepositorioBase):
    """Historial de cambios. Todo lo que se escribe en el sistema deja una línea."""

    def anotar(self, fecha_hora: datetime, accion: str, detalle: str = "") -> None:
        self._bd.ejecutar(
            "INSERT INTO bitacora (fecha_hora, accion, detalle) VALUES (?, ?, ?)",
            (_a_texto(fecha_hora), accion, detalle),
        )

    def listar(self, limite: int = 100) -> List[RegistroBitacora]:
        """Lo más reciente primero. La bitácora solo crece: no hay forma de borrarla."""
        filas = self._bd.todos(
            """
            SELECT fecha_hora, accion, detalle
              FROM bitacora ORDER BY id_registro DESC LIMIT ?
            """,
            (limite,),
        )
        return [
            RegistroBitacora(datetime.fromisoformat(f["fecha_hora"]), f["accion"], f["detalle"])
            for f in filas
        ]
