# Verificación del prototipo

Fecha: 31 de octubre de 2026. Entorno: Windows 11 x64, Python 3.14.6 x64, PyNaCl 1.6.2, PySide6 6.10.2. Exclusivamente archivos sintéticos. No se accedió a una cuenta TeraBox ni se movieron archivos reales del usuario.

## Pruebas automatizadas

**20 pruebas aprobadas** en 12,789 segundos mediante `python -m unittest -v test_vault test_ui`.

- Ida/vuelta para vacío, 1 byte, 1 MiB−1, 1 MiB, 1 MiB+1 y 2 MiB; nombres recuperados y conservación de originales.
- Contraseña incorrecta y validación de parámetros hostiles antes de ejecutar Argon2id.
- Alteración, truncado, reordenación, datos adicionales, longitudes de bloque maliciosas e identidad de archivo renombrada: rechazo sin publicar texto claro parcial.
- Rutas peligrosas y nombres reservados Windows; prueba de metadatos peligrosos autenticados, no sólo de una función de validación.
- Rechazo de texto claro y temporales dentro de la bóveda y de otras subcarpetas del área de nube declarada. No sobrescritura del recuperado existente.
- Cancelación de cifrado y recuperación; eliminación del parcial, conservación del origen y fallo simulado de publicación.
- Rotación real: clave independiente, contraseña nueva, recuperación idéntica y bóveda anterior utilizable e intacta. Contraseña actual obligatoria.
- Migración cancelada o con verificación fallida: estado incompleto y origen conservado.
- Limpieza: confirmación manual obligatoria, archivos ajenos/subcarpetas/originales conservados; rechazo ante corrupción nueva o cambio del cifrado antiguo; interrupción a mitad de limpieza y repetición segura.
- Streaming real de un objeto de **80 MiB** en disco. Pico medido con `tracemalloc`: **3,26 MiB de asignaciones de Python** durante cifrado/recuperación. No representa RAM total: excluye memoria nativa, los 64 MiB de Argon2id y Qt. No extrapolar como medición de terabytes reales.
- Qt en modo offscreen: recepción de un evento de arrastre/soltado con URLs de archivos locales, generación de URLs nativas de salida y portapapeles MIME de archivos; rechazo de URLs web y carpetas.

El punto de entrada fuente también pasó `--smoke-test`: arrancó Qt y completó cifrado, rotación, recuperación y limpieza con datos sintéticos. Se renderizó e inspeccionó visualmente `vista_previa.png`, una demostración con nombres ficticios. Se comprobó que Qt reconoce 332 familias tipográficas con el backend Windows de esta máquina.

## Ejecutable

Construido con PyInstaller 6.22.3, hooks 2026.9, formato `--onefile --windowed`, Python x64 y bibliotecas incluidas. Se corrigieron dos problemas detectados en pruebas: la omisión de `_cffi_backend` y la recogida de una DLL ICU ajena desde PATH que impedía cargar Qt. La receta entregada incluye el backend explícitamente y excluye esas DLL ICU; se utiliza la interfaz ICU de Windows. No se modificó la configuración global del equipo.

**El ejecutable final pasó la prueba de arranque real con el backend Windows y terminó con código 0.** El informe `prueba_exe.json` confirma: interfaz iniciada, proceso de 64 bits, ejecución empaquetada (`frozen`), cifrado/recuperación idéntica, rotación completa y limpieza limitada. Se ejecutó sin mostrar ventanas durante la prueba y sin invocar un Python externo desde el binario. La cabecera PE fue inspeccionada: máquina `0x8664` (AMD64). `SHA256SUMS.txt` identifica el binario y los demás entregables.

## Límites pendientes

- No se han probado una cuenta real, configuración concreta, carga, descarga, hidratación de placeholders, propagación de borrados ni retención remota de TeraBox u otra nube. La subida sólo se confirma manualmente mediante el aviso del cliente. No hay API ni credenciales en la app.
- No se ha ensayado un arrastre físico de Explorer a la ventana y viceversa, ni pegar físicamente en Explorer: están implementados y se probaron sus eventos/URLs/MIME, pero requieren validación manual en escritorio real. No se afirma que esas pruebas de sistema completo estén hechas.
- No se han procesado archivos reales de más de 50 GB ni terabytes. No se han medido rendimiento sostenido, RAM total, discos llenos reales, desconexiones de volumen, cortes de energía ni todas las condiciones de Windows/antivirus/proveedor. El fallo de publicación se simuló; los casos de integridad y cancelación sí usaron archivos reales sintéticos.
- No se ha probado el portable en un PC limpio sin Python ni en todas las versiones de Windows. Su empaquetado incluye el intérprete; la prueba de arranque se ejecuta en esta máquina de construcción.
- La navegación es una lista plana ordenada y filtrable con menú contextual. No hay importación de carpetas recursiva, creación/renombrado de subcarpetas, unidad virtual, visor de contenidos, reanudación de migración ni aplicación móvil.
- No es un producto auditado. Un equipo o proceso del mismo usuario hostil y modificaciones concurrentes están fuera del modelo del prototipo. No hay recuperación de contraseña ni borrado forense.
