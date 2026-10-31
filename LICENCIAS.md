# Componentes incluidos

Los textos recibidos con las dependencias se conservan en `licencias/`; también se incluyen LGPLv3 y GPLv3 para Qt y el aviso de Python. El código de este prototipo y su receta de construcción se entregan completos para inspección, modificación y reconstrucción.

- Python 3.14.6, [fuentes oficiales](https://www.python.org/downloads/source/), licencia PSF y avisos asociados.
- PyNaCl 1.6.2, [fuentes](https://github.com/pyca/pynacl/tree/1.6.2), Apache 2.0; libsodium incorporada, licencia ISC.
- cffi 2.1.1 y pycparser 3.12: licencias MIT/BSD según sus avisos adjuntos.
- PySide6 / Qt / shiboken6 6.10.2: términos de código abierto LGPLv3 o GPL según los componentes. Se usan Core, Gui, Widgets y dependencias distribuidas por los hooks de Qt; no se incorporan módulos opcionales de la app comercial. [Avisos de Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html), [fuentes de PySide](https://code.qt.io/cgit/pyside/pyside-setup.git/?h=6.10.2), [fuentes de Qt](https://download.qt.io/archive/qt/6.10/6.10.2/).
- PyInstaller 6.22.3 y hooks 2026.9, herramienta de construcción con excepción de distribución del bootloader; avisos incluidos.

Para sustituir las bibliotecas Qt/PySide utilizadas por el ejecutable, modifique las dependencias de `requirements.txt` o instale las versiones modificadas en el entorno de construcción y ejecute el comando de PyInstaller de `build.ps1`. No se impone restricción de ingeniería inversa sobre las bibliotecas para depurar sus modificaciones. El formato de archivo de la bóveda es independiente de la interfaz Qt.
