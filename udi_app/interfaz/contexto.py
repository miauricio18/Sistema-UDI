"""Lo que cada pantalla recibe para trabajar.

Las pantallas no conocen la ventana principal ni los diálogos concretos: solo
este objeto. Así una pantalla se puede probar entregándole un contexto falso
(avisos que no se dibujan, una confirmación que siempre dice que sí).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, NamedTuple, Optional, Protocol, Sequence

from udi.aplicacion import Servicios
from udi.excepciones import ErrorUDI


class Avisos(Protocol):
    """Lugar donde se muestran los mensajes cortos para la persona."""

    def exito(self, mensaje: str) -> None: ...

    def error(self, mensaje: str) -> None: ...

    def info(self, mensaje: str) -> None: ...


class Resultado(NamedTuple):
    """Cómo terminó una llamada al backend."""

    ok: bool
    valor: Any = None


Confirmar = Callable[..., bool]
ElegirArchivo = Callable[[str, Sequence[str]], Optional[Path]]
PedirDatos = Callable[..., Optional[Dict[str, str]]]
MostrarTexto = Callable[[str, str], None]


@dataclass
class Contexto:
    servicios: Servicios
    avisos: Avisos
    navegar: Callable[[str], None]
    confirmar: Confirmar
    elegir_archivo: ElegirArchivo
    pedir_datos: PedirDatos
    mostrar_texto: MostrarTexto

    def intentar(
        self, accion: Callable[[], Any], exito: Optional[str] = None, avisar: bool = True
    ) -> Resultado:
        """Llama al backend y traduce el resultado a un aviso.

        Es el único lugar donde la interfaz atrapa ``ErrorUDI``: el mensaje
        del error ya viene escrito para la persona y se muestra tal cual.
        Con ``avisar=False`` el error no se muestra (sirve para consultas en
        las que "no hay" es una respuesta normal).
        """
        try:
            valor = accion()
        except ErrorUDI as error:
            if avisar:
                self.avisos.error(error.mensaje)
            return Resultado(False)
        if exito:
            self.avisos.exito(exito)
        return Resultado(True, valor)
