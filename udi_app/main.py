"""Punto de entrada de la aplicación de escritorio.

    python main.py             datos reales en Documentos\\UDI
    python main.py --ejemplo   datos ficticios en memoria (no guarda nada)
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence


def main(argumentos: Optional[Sequence[str]] = None) -> int:
    opciones = argparse.ArgumentParser(description="Asistencia y equipos de las UDI")
    opciones.add_argument("--ejemplo", action="store_true",
                          help="usa datos ficticios en memoria; no guarda nada")
    datos_ejemplo = opciones.parse_args(argumentos).ejemplo

    try:
        from interfaz.app import Aplicacion
        from udi.aplicacion import iniciar

        servicios = iniciar(datos_ejemplo=datos_ejemplo)
    except Exception as error:  # sin base de datos no hay nada que mostrar
        _avisar_fallo_de_arranque(error)
        return 1

    try:
        Aplicacion(servicios).ejecutar()
    finally:
        servicios.cerrar()
    return 0


def _avisar_fallo_de_arranque(error: Exception) -> None:
    mensaje = getattr(error, "mensaje", None) or f"{type(error).__name__}: {error}"
    try:
        import tkinter
        from tkinter import messagebox

        raiz = tkinter.Tk()
        raiz.withdraw()
        messagebox.showerror("UDI", f"La aplicación no pudo iniciar.\n\n{mensaje}")
        raiz.destroy()
    except Exception:
        print(f"La aplicación no pudo iniciar. {mensaje}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
