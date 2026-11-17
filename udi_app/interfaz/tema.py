"""Apariencia de toda la interfaz: colores, tamaños, fuentes y estilos.

Ninguna pantalla escribe un color o un tamaño a mano: los toma de aquí. Para
cambiar el aspecto de la aplicación completa se edita solo este archivo.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Tuple


class Color:
    """Paleta. El acento es el guinda del IPN; lo demás es neutro."""

    FONDO = "#FFFFFF"
    LATERAL = "#F4F5F7"
    BORDE = "#DCE0E5"
    TEXTO = "#1B1F24"
    TEXTO_SUAVE = "#5C6773"
    INACTIVO = "#EDEFF2"

    ACENTO = "#7A1F3D"
    ACENTO_OSCURO = "#5E162E"
    ACENTO_SUAVE = "#F6E9EE"
    SOBRE_ACENTO = "#FFFFFF"

    EXITO = "#1E7B45"
    EXITO_SUAVE = "#E6F4EB"
    ALERTA = "#9A6200"
    ALERTA_SUAVE = "#FCF1DC"
    ERROR = "#B3261E"
    ERROR_SUAVE = "#FBEAE9"


class Medida:
    """Espacios y tamaños en pixeles. Todo espacio es múltiplo de UNIDAD."""

    UNIDAD = 8
    MARGEN = 24            # borde de cada pantalla
    ALTO_FILA = 36         # filas de las tablas
    ANCHO_LATERAL = 216
    ANCHO_PANEL = 312      # panel de captura del pase de lista
    VENTANA = "1280x800"
    VENTANA_MINIMA = (1100, 700)


class Estilo:
    """Nombres de los estilos ttk, para no repetir textos sueltos."""

    BOTON = "TButton"
    PRIMARIO = "Primario.TButton"
    PELIGRO = "Peligro.TButton"
    TECLA = "Tecla.TButton"
    NAV = "Nav.TButton"
    NAV_ACTIVO = "NavActivo.TButton"
    SEGMENTO = "Segmento.TButton"
    SEGMENTO_ACTIVO = "SegmentoActivo.TButton"

    TITULO = "Titulo.TLabel"
    SUBTITULO = "Subtitulo.TLabel"
    SUAVE = "Suave.TLabel"
    DESTACADO = "Destacado.TLabel"
    MARCA = "Marca.TLabel"
    LATERAL_SUAVE = "LateralSuave.TLabel"

    LATERAL = "Lateral.TFrame"
    LINEA = "Linea.TFrame"
    ENTRADA_GRANDE = "Grande.TEntry"


_FAMILIAS_PREFERIDAS = ("Segoe UI", "Inter", "Helvetica Neue", "DejaVu Sans")
_familia = "TkDefaultFont"


def fuente(tamano: int = 11, negrita: bool = False) -> Tuple[str, int, str]:
    """Fuente de la aplicación en el tamaño pedido (en puntos)."""
    return (_familia, tamano, "bold" if negrita else "normal")


def aplicar_tema(raiz: tk.Misc) -> None:
    """Configura los estilos una sola vez, al crear la ventana."""
    global _familia
    disponibles = set(tkfont.families(raiz))
    _familia = next((f for f in _FAMILIAS_PREFERIDAS if f in disponibles), _familia)

    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    raiz.configure(background=Color.FONDO)
    # Las fuentes con nombre de Tk son las que usan los controles que no fijan una.
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nombre, root=raiz).configure(family=_familia, size=11)
    raiz.option_add("*TCombobox*Listbox.font", fuente())
    raiz.option_add("*TCombobox*Listbox.selectBackground", Color.ACENTO)
    raiz.option_add("*TCombobox*Listbox.selectForeground", Color.SOBRE_ACENTO)

    estilo.configure(".", font=fuente(), background=Color.FONDO, foreground=Color.TEXTO,
                     bordercolor=Color.BORDE, lightcolor=Color.FONDO, darkcolor=Color.FONDO,
                     focuscolor=Color.ACENTO)

    _marcos(estilo)
    _etiquetas(estilo)
    _botones(estilo)
    _campos(estilo)
    _tablas(estilo)


def _marcos(estilo: ttk.Style) -> None:
    estilo.configure("TFrame", background=Color.FONDO)
    estilo.configure(Estilo.LATERAL, background=Color.LATERAL)
    estilo.configure(Estilo.LINEA, background=Color.BORDE)


def _etiquetas(estilo: ttk.Style) -> None:
    estilo.configure("TLabel", background=Color.FONDO, foreground=Color.TEXTO)
    estilo.configure(Estilo.TITULO, font=fuente(20, True))
    estilo.configure(Estilo.SUBTITULO, font=fuente(13, True))
    estilo.configure(Estilo.DESTACADO, font=fuente(16, True))
    estilo.configure(Estilo.SUAVE, foreground=Color.TEXTO_SUAVE)
    estilo.configure(Estilo.MARCA, background=Color.LATERAL, foreground=Color.ACENTO,
                     font=fuente(15, True))
    estilo.configure(Estilo.LATERAL_SUAVE, background=Color.LATERAL,
                     foreground=Color.TEXTO_SUAVE)


def _botones(estilo: ttk.Style) -> None:
    # Alto mínimo cómodo para el dedo: texto + 2 x 10 px de relleno.
    estilo.configure(Estilo.BOTON, padding=(16, 10), background=Color.FONDO,
                     foreground=Color.TEXTO, bordercolor=Color.BORDE, relief="raised",
                     lightcolor=Color.FONDO, darkcolor=Color.FONDO,
                     borderwidth=1, focusthickness=1)
    estilo.map(Estilo.BOTON,
               background=[("disabled", Color.INACTIVO), ("pressed", Color.INACTIVO),
                           ("active", Color.LATERAL)],
               lightcolor=[("disabled", Color.INACTIVO), ("pressed", Color.INACTIVO),
                           ("active", Color.LATERAL)],
               darkcolor=[("disabled", Color.INACTIVO), ("pressed", Color.INACTIVO),
                          ("active", Color.LATERAL)],
               foreground=[("disabled", Color.TEXTO_SUAVE)])

    estilo.configure(Estilo.PRIMARIO, background=Color.ACENTO, foreground=Color.SOBRE_ACENTO,
                     bordercolor=Color.ACENTO, lightcolor=Color.ACENTO, darkcolor=Color.ACENTO,
                     font=fuente(11, True))
    estilo.map(Estilo.PRIMARIO,
               background=[("disabled", Color.INACTIVO), ("pressed", Color.ACENTO_OSCURO),
                           ("active", Color.ACENTO_OSCURO)],
               lightcolor=[("disabled", Color.INACTIVO), ("pressed", Color.ACENTO_OSCURO),
                           ("active", Color.ACENTO_OSCURO)],
               darkcolor=[("disabled", Color.INACTIVO), ("pressed", Color.ACENTO_OSCURO),
                          ("active", Color.ACENTO_OSCURO)],
               foreground=[("disabled", Color.TEXTO_SUAVE)],
               bordercolor=[("disabled", Color.BORDE)])

    estilo.configure(Estilo.PELIGRO, foreground=Color.ERROR)
    estilo.map(Estilo.PELIGRO,
               background=[("disabled", Color.INACTIVO), ("pressed", Color.ERROR_SUAVE),
                           ("active", Color.ERROR_SUAVE)],
               lightcolor=[("disabled", Color.INACTIVO), ("active", Color.ERROR_SUAVE)],
               darkcolor=[("disabled", Color.INACTIVO), ("active", Color.ERROR_SUAVE)],
               foreground=[("disabled", Color.TEXTO_SUAVE)])

    estilo.configure(Estilo.TECLA, padding=(0, 12), font=fuente(16))

    _plano(estilo, Estilo.NAV, Color.LATERAL, Color.INACTIVO, padding=(16, 12), anchor="w",
           foreground=Color.TEXTO)
    _plano(estilo, Estilo.NAV_ACTIVO, Color.ACENTO_SUAVE, Color.ACENTO_SUAVE, padding=(16, 12),
           anchor="w", foreground=Color.ACENTO, font=fuente(11, True))

    estilo.configure(Estilo.SEGMENTO, padding=(12, 8))
    _plano(estilo, Estilo.SEGMENTO_ACTIVO, Color.ACENTO_SUAVE, Color.ACENTO_SUAVE,
           padding=(12, 8), foreground=Color.ACENTO, font=fuente(11, True))
    estilo.configure(Estilo.SEGMENTO_ACTIVO, bordercolor=Color.ACENTO)
    estilo.map(Estilo.SEGMENTO_ACTIVO, bordercolor=[("active", Color.ACENTO)])


def _plano(estilo: ttk.Style, nombre: str, fondo: str, fondo_activo: str, **opciones) -> None:
    """Botón de un solo color, sin borde visible (menú y opción marcada)."""
    estilo.configure(nombre, background=fondo, bordercolor=fondo, lightcolor=fondo,
                     darkcolor=fondo, **opciones)
    estados = [("pressed", fondo_activo), ("active", fondo_activo)]
    estilo.map(nombre, background=estados, bordercolor=estados, lightcolor=estados,
               darkcolor=estados)


def _campos(estilo: ttk.Style) -> None:
    for nombre in ("TEntry", "TCombobox"):
        estilo.configure(nombre, padding=8, fieldbackground=Color.FONDO,
                         bordercolor=Color.BORDE, foreground=Color.TEXTO,
                         arrowcolor=Color.TEXTO_SUAVE, background=Color.FONDO)
        estilo.map(nombre, bordercolor=[("focus", Color.ACENTO)],
                   lightcolor=[("focus", Color.ACENTO)], darkcolor=[("focus", Color.ACENTO)],
                   fieldbackground=[("readonly", Color.FONDO), ("disabled", Color.INACTIVO)],
                   selectbackground=[("readonly", Color.FONDO)],
                   selectforeground=[("readonly", Color.TEXTO)])
    estilo.configure(Estilo.ENTRADA_GRANDE, padding=10)
    estilo.configure("TCheckbutton", background=Color.FONDO, padding=(0, 6),
                     indicatorsize=18, indicatormargin=(0, 0, 8, 0),
                     indicatorbackground=Color.FONDO, indicatorforeground=Color.ACENTO)
    estilo.map("TCheckbutton", background=[("active", Color.FONDO)],
               foreground=[("disabled", Color.TEXTO_SUAVE)],
               indicatorbackground=[("disabled", Color.INACTIVO)])
    estilo.configure("Vertical.TScrollbar", background=Color.BORDE,
                     troughcolor=Color.FONDO, bordercolor=Color.FONDO, lightcolor=Color.BORDE,
                     darkcolor=Color.BORDE, arrowcolor=Color.TEXTO_SUAVE, relief="flat")
    estilo.map("Vertical.TScrollbar",
               background=[("disabled", Color.FONDO), ("active", Color.TEXTO_SUAVE)],
               lightcolor=[("disabled", Color.FONDO)], darkcolor=[("disabled", Color.FONDO)],
               arrowcolor=[("disabled", Color.FONDO)])


def _tablas(estilo: ttk.Style) -> None:
    estilo.configure("Treeview", rowheight=Medida.ALTO_FILA, background=Color.FONDO,
                     fieldbackground=Color.FONDO, foreground=Color.TEXTO,
                     bordercolor=Color.BORDE, borderwidth=1)
    estilo.map("Treeview", background=[("selected", Color.ACENTO_SUAVE)],
               foreground=[("selected", Color.TEXTO)])
    estilo.configure("Treeview.Heading", font=fuente(10, True), padding=(8, 8),
                     background=Color.LATERAL, foreground=Color.TEXTO_SUAVE,
                     relief="flat", bordercolor=Color.BORDE)
    estilo.map("Treeview.Heading", background=[("active", Color.LATERAL)])
