"""Errores propios del sistema.

Todos heredan de ErrorUDI y traen un ``codigo`` estable y un ``mensaje`` en
español listo para mostrarse tal cual en la pantalla.
"""

from __future__ import annotations

from typing import Optional


class ErrorUDI(Exception):
    """Base de todos los errores que el sistema avisa a la interfaz."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class AlumnoNoEncontrado(ErrorUDI):
    def __init__(self) -> None:
        super().__init__(
            "alumno_no_encontrado",
            "No reconocemos esa credencial. Búscalo en la lista.",
        )


class GrupoDistinto(ErrorUDI):
    def __init__(self, nombre_alumno: str, clase_que_le_toca: Optional[str]) -> None:
        if clase_que_le_toca:
            mensaje = (
                f"{nombre_alumno} no es de este grupo. "
                f"Hoy le toca: {clase_que_le_toca}."
            )
        else:
            mensaje = f"{nombre_alumno} no es de este grupo y hoy no tiene clase."
        super().__init__("grupo_distinto", mensaje)
        self.clase_que_le_toca = clase_que_le_toca


class EquipoOcupado(ErrorUDI):
    def __init__(self, numero_equipo: int, ocupado_por: str) -> None:
        super().__init__(
            "equipo_ocupado",
            f"La computadora {numero_equipo} ya la usa {ocupado_por}. Elige otra.",
        )


class EquipoFueraDeServicio(ErrorUDI):
    def __init__(self, numero_equipo: int) -> None:
        super().__init__(
            "equipo_fuera_de_servicio",
            f"La computadora {numero_equipo} está fuera de servicio. Elige otra.",
        )


class EquipoNoEncontrado(ErrorUDI):
    def __init__(self, id_laboratorio: str, numero_equipo: int) -> None:
        super().__init__(
            "equipo_no_encontrado",
            f"No existe la computadora {numero_equipo} en el laboratorio {id_laboratorio}.",
        )


class PaseListaCerrado(ErrorUDI):
    def __init__(self) -> None:
        super().__init__(
            "pase_lista_cerrado",
            "El pase de lista ya está cerrado. Reábrelo para registrar a alguien.",
        )


class SesionNoEncontrada(ErrorUDI):
    def __init__(self) -> None:
        super().__init__(
            "sesion_no_encontrada",
            "No hay una clase para registrar en este momento.",
        )


class GrupoNoEncontrado(ErrorUDI):
    def __init__(self, clave_grupo: str) -> None:
        super().__init__("grupo_no_encontrado", f"No existe el grupo {clave_grupo}.")


class LaboratorioNoEncontrado(ErrorUDI):
    def __init__(self, id_laboratorio: str) -> None:
        super().__init__(
            "laboratorio_no_encontrado", f"No existe el laboratorio {id_laboratorio}."
        )


class HorarioEmpalmado(ErrorUDI):
    def __init__(self, id_laboratorio: str, clase_existente: str) -> None:
        super().__init__(
            "horario_empalmado",
            f"El laboratorio {id_laboratorio} ya está ocupado a esa hora por {clase_existente}.",
        )


class ArchivoInvalido(ErrorUDI):
    def __init__(self, motivo: str) -> None:
        super().__init__("archivo_invalido", f"No se pudo usar el archivo: {motivo}")


class DatosInvalidos(ErrorUDI):
    """Datos que el sistema no puede aceptar (texto vacío, horario al revés, etc.)."""

    def __init__(self, mensaje: str) -> None:
        super().__init__("datos_invalidos", mensaje)


# --------------------------------------------------------------------------- #
# Mantenimiento
# --------------------------------------------------------------------------- #
class ErrorRespaldo(ErrorUDI):
    def __init__(self, motivo: str) -> None:
        super().__init__("error_respaldo", f"No se pudo crear el respaldo: {motivo}")


class RespaldoInvalido(ErrorUDI):
    def __init__(self, motivo: str) -> None:
        super().__init__("respaldo_invalido", f"No se pudo usar el respaldo: {motivo}")
