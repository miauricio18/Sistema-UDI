"""Ventanas que piden algo antes de continuar: confirmar, llenar datos, elegir archivo.

Las pantallas no las llaman directamente: las reciben dentro del ``Contexto``.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Dict, NamedTuple, Optional, Sequence

from ..tema import Color, Estilo, Medida, fuente

_ANCHO_TEXTO = 420


class Campo(NamedTuple):
    """Un dato que se pide en un formulario. Con ``opciones`` se elige de una lista."""

    clave: str
    etiqueta: str
    valor: str = ""
    opciones: Sequence[str] = ()
    ayuda: str = ""


class _Dialogo(tk.Toplevel):
    """Base: ventana centrada sobre la aplicación que bloquea lo demás hasta cerrarse."""

    def __init__(self, padre: tk.Misc, titulo: str) -> None:
        super().__init__(padre, background=Color.FONDO)
        self.withdraw()
        self.title(titulo)
        self.resizable(False, False)
        self.transient(padre.winfo_toplevel())
        self.cuerpo = ttk.Frame(self, padding=Medida.MARGEN)
        self.cuerpo.pack(fill="both", expand=True)
        ttk.Label(self.cuerpo, text=titulo, style=Estilo.SUBTITULO).pack(anchor="w")
        self.bind("<Escape>", lambda _evento: self.cancelar())
        self.protocol("WM_DELETE_WINDOW", self.cancelar)

    def botones(self, texto_aceptar: str, estilo: str = Estilo.PRIMARIO,
                texto_cancelar: Optional[str] = "Cancelar") -> None:
        fila = ttk.Frame(self.cuerpo)
        fila.pack(fill="x", pady=(Medida.MARGEN, 0))
        ttk.Button(fila, text=texto_aceptar, style=estilo, command=self.aceptar).pack(side="right")
        if texto_cancelar:
            ttk.Button(fila, text=texto_cancelar, command=self.cancelar).pack(
                side="right", padx=(0, Medida.UNIDAD))

    def esperar(self) -> None:
        self.update_idletasks()
        principal = self.master.winfo_toplevel()
        x = principal.winfo_rootx() + (principal.winfo_width() - self.winfo_reqwidth()) // 2
        y = principal.winfo_rooty() + (principal.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.grab_set()
        self.focus_set()
        self.wait_window()

    def aceptar(self) -> None:
        self.destroy()

    def cancelar(self) -> None:
        self.destroy()


class _Confirmacion(_Dialogo):
    def __init__(self, padre: tk.Misc, titulo: str, mensaje: str, texto_si: str, peligro: bool) -> None:
        super().__init__(padre, titulo)
        self.respuesta = False
        ttk.Label(self.cuerpo, text=mensaje, wraplength=_ANCHO_TEXTO, justify="left").pack(
            anchor="w", pady=(Medida.UNIDAD, 0))
        self.botones(texto_si, Estilo.PELIGRO if peligro else Estilo.PRIMARIO)

    def aceptar(self) -> None:
        self.respuesta = True
        self.destroy()


class _Formulario(_Dialogo):
    def __init__(self, padre: tk.Misc, titulo: str, campos: Sequence[Campo], texto_aceptar: str) -> None:
        super().__init__(padre, titulo)
        self.respuesta: Optional[Dict[str, str]] = None
        self._variables: Dict[str, tk.StringVar] = {}
        for campo in campos:
            ttk.Label(self.cuerpo, text=campo.etiqueta, style=Estilo.SUAVE).pack(
                anchor="w", pady=(Medida.UNIDAD * 2, 4))
            variable = tk.StringVar(self, value=campo.valor)
            if campo.opciones:
                entrada: ttk.Entry = ttk.Combobox(
                    self.cuerpo, textvariable=variable, values=list(campo.opciones),
                    state="readonly", width=44)
            else:
                entrada = ttk.Entry(self.cuerpo, textvariable=variable, width=46)
            entrada.pack(fill="x")
            if campo.ayuda:
                ttk.Label(self.cuerpo, text=campo.ayuda, style=Estilo.SUAVE,
                          font=fuente(9)).pack(anchor="w", pady=(2, 0))
            if not self._variables:
                entrada.focus_set()
            self._variables[campo.clave] = variable
        self.botones(texto_aceptar)
        self.bind("<Return>", lambda _evento: self.aceptar())

    def aceptar(self) -> None:
        self.respuesta = {clave: variable.get().strip() for clave, variable in self._variables.items()}
        self.destroy()


class _Texto(_Dialogo):
    def __init__(self, padre: tk.Misc, titulo: str, texto: str) -> None:
        super().__init__(padre, titulo)
        marco = ttk.Frame(self.cuerpo)
        marco.pack(fill="both", expand=True, pady=(Medida.UNIDAD, 0))
        caja = tk.Text(marco, width=64, height=14, wrap="word", font=fuente(10),
                       relief="flat", background=Color.LATERAL, padx=12, pady=12)
        barra = ttk.Scrollbar(marco, orient="vertical", command=caja.yview)
        caja.configure(yscrollcommand=barra.set)
        caja.insert("1.0", texto)
        caja.configure(state="disabled")
        caja.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.botones("Cerrar", texto_cancelar=None)


# --------------------------------------------------------------------------- #
# Funciones que usa la aplicación para armar el Contexto
# --------------------------------------------------------------------------- #
def confirmar(padre: tk.Misc, titulo: str, mensaje: str, texto_si: str = "Aceptar",
              peligro: bool = False) -> bool:
    dialogo = _Confirmacion(padre, titulo, mensaje, texto_si, peligro)
    dialogo.esperar()
    return dialogo.respuesta


def pedir_datos(padre: tk.Misc, titulo: str, campos: Sequence[Campo],
                texto_aceptar: str = "Guardar") -> Optional[Dict[str, str]]:
    dialogo = _Formulario(padre, titulo, campos, texto_aceptar)
    dialogo.esperar()
    return dialogo.respuesta


def mostrar_texto(padre: tk.Misc, titulo: str, texto: str) -> None:
    _Texto(padre, titulo, texto).esperar()


def elegir_archivo(padre: tk.Misc, titulo: str, extensiones: Sequence[str]) -> Optional[Path]:
    patron = " ".join(f"*{extension}" for extension in extensiones)
    ruta = filedialog.askopenfilename(
        parent=padre, title=titulo, filetypes=[("Archivos permitidos", patron)])
    return Path(ruta) if ruta else None
