"""Pantallas de la aplicación, en el orden en que aparecen en el menú.

Para agregar una: crear su archivo en esta carpeta y sumarla a ``PANTALLAS``.
"""

from typing import Tuple, Type

from .administracion import PantallaAdministracion
from .base import Pantalla
from .estadisticas import PantallaEstadisticas
from .horario import PantallaHorario
from .pase_lista import PantallaPaseLista
from .reportes import PantallaReportes

PANTALLAS: Tuple[Type[Pantalla], ...] = (
    PantallaPaseLista,
    PantallaHorario,
    PantallaReportes,
    PantallaEstadisticas,
    PantallaAdministracion,
)
