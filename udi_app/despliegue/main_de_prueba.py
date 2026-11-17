"""Sustituto de main.py para probar el empaquetado antes de tener la interfaz.

Usa datos de ejemplo en memoria: no toca la carpeta Documentos\\UDI.
Si al final dice "TODO FUNCIONA", el paquete trae todo lo necesario.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from udi import __version__
from udi.aplicacion import iniciar
from udi.modelos import Periodo


def main() -> int:
    print(f"Sistema UDI {__version__} - prueba de empaquetado")
    servicios = iniciar(datos_ejemplo=True)
    try:
        clase = servicios.asistencia.obtener_sesion_actual()
        alumno = servicios.asistencia.obtener_lista(clase.id_sesion)[0].alumno
        servicios.asistencia.asignar_equipo(clase.id_sesion, alumno.boleta, 1)
        print(f"  Clase actual: {clase.grupo.materia} en {clase.id_laboratorio}")
        print(f"  Llegada registrada: {alumno.nombre}, computadora 1")
        with tempfile.TemporaryDirectory() as carpeta:
            salida = servicios.archivos.exportar_excel(
                Periodo.semestre(), Path(carpeta) / "prueba.xlsx"
            )
            print(f"  Excel generado: {salida.stat().st_size} bytes")
        print("TODO FUNCIONA")
        return 0
    finally:
        servicios.cerrar()


if __name__ == "__main__":
    codigo = main()
    if sys.stdin and sys.stdin.isatty():
        input("Presiona Enter para cerrar...")
    raise SystemExit(codigo)
