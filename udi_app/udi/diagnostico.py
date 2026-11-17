"""Revisión rápida de la instalación. Uso: ``python -m udi.diagnostico``.

No cambia datos de asistencia: solo abre la base (la crea si es
la primera vez), revisa que esté sana y muestra dónde quedó todo.
"""

from __future__ import annotations

from . import __version__
from .base_datos import BaseDatos
from .configuracion import Configuracion
from .respaldos import PATRON_ARCHIVOS


def main() -> int:
    configuracion = Configuracion()
    base_datos = BaseDatos(configuracion)
    try:
        base_datos.crear_tablas()
        problemas = base_datos.verificar_integridad()
        respaldos = len(list(configuracion.carpeta_respaldos.glob(PATRON_ARCHIVOS)))
        print(f"Sistema UDI          {__version__}")
        print(f"Carpeta de datos     {configuracion.carpeta_datos}")
        print(f"Versión del esquema  {base_datos.version_esquema}")
        print(f"Tamaño de la base    {base_datos.tamano_bytes / 1024:.0f} KB")
        print(f"Respaldos guardados  {respaldos}")
        print(f"Integridad           {'correcta' if not problemas else 'CON PROBLEMAS'}")
        for problema in problemas:
            print(f"  - {problema}")
        return 1 if problemas else 0
    finally:
        base_datos.cerrar()


if __name__ == "__main__":
    raise SystemExit(main())
