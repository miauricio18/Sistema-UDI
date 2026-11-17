# Sistema UDI

Asistencia y uso de computadoras en las UDI. Aplicación de escritorio para la tableta de la encargada. Versión 1.0.0.

## Probarla en un minuto

```
pip install -r requirements.txt
python main.py --ejemplo
```

`--ejemplo` abre la aplicación con datos ficticios en memoria: no guarda nada. Sin esa opción usa los datos reales de `Documentos\UDI`.

En Linux, Tkinter se instala aparte (`sudo apt install python3-tk`). En Windows ya viene con Python.

## Comandos

| Para | Comando |
| --- | --- |
| Instalar todo lo de desarrollo | `pip install -r requirements.txt -r requirements-dev.txt` |
| Abrir la aplicación | `python main.py` |
| Correr las pruebas | `python -m pytest` |
| Revisar una instalación | `python -m udi.diagnostico` |
| Construir la carpeta para la tableta (Windows) | `despliegue\construir.bat` |

## Carpetas

```
main.py            punto de entrada
udi/               backend: reglas, base de datos, archivos (no sabe que existe la interfaz)
  servicios/       lo único que la interfaz llama
interfaz/          frontend en Tkinter (no contiene reglas)
  tema.py          colores, tamaños y estilos de toda la aplicación
  textos.py        cómo se escribe cada dato en pantalla
  contexto.py      lo que recibe cada pantalla para trabajar
  app.py           ventana, menú y navegación
  componentes/     piezas reutilizables (tabla, teclado, mapa, diálogos...)
  pantallas/       una pantalla por archivo
pruebas/           pruebas automáticas (backend e interfaz)
despliegue/        empaquetado para la tableta
```

## Reglas para trabajar en equipo

1. La interfaz solo habla con `servicios.*`. Nunca importa `udi.repositorio` ni `udi.base_datos`.
2. Las reglas van en `udi/servicios/`; las pantallas solo dibujan y llaman.
3. Colores, tamaños y fuentes salen de `interfaz/tema.py`. Los textos de estados, de `interfaz/textos.py`.
4. Cada pantalla vive en su archivo. Para agregar una: crear la clase en `interfaz/pantallas/` y sumarla a `PANTALLAS` en `interfaz/pantallas/__init__.py`.
5. Toda llamada al backend desde una pantalla pasa por `self.contexto.intentar(...)`, que muestra el aviso si algo falla.
6. No se entrega un cambio si `python -m pytest` no pasa completo.

En la tableta los datos quedan en `Documentos\UDI`: `udi.db`, `respaldos\`, `exportaciones\` y `logs\`.
