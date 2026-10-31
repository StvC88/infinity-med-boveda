# Infinity Med · revisión v2

## Implementado

- Logo Infinity Med del material aportado, adaptado sobre transparencia, en encabezado e icono; texto regular Segoe UI, carpetas de colores, encabezados en español y rutas completas sólo en la ayuda emergente.
- Bloquear oculta el explorador recuperado, limpia selección y búsqueda y retira la clave activa. Conserva los archivos finales ya recuperados; no pretende borrarlos ni retirarlos de otras aplicaciones.
- Los parciales de operación no permiten selección/arrastre individual desde Desencriptados y el panel queda deshabilitado durante operaciones.
- Botón Verificar repositorio: recorre y autentica cada archivo, comprueba fin y tamaño, y compara con un inventario autenticado. No produce texto claro en disco.
- Nuevo encabezado v2 con inventario obligatorio. Detecta objetos desaparecidos, objetos extra e inventario eliminado o alterado. La app abre encabezados v1 existentes y avisa que carecen de inventario. Migrar a otra bóveda genera v2 y clave nueva.
- Publicación del objeto y del inventario con temporales cifrados fuera de nube. Si una interrupción deja un objeto completo sin registrar, la verificación lo detecta y bloquea nuevas importaciones; no elimina el objeto y puede recuperarse individualmente. No hay reparación automática ni una transacción distribuida con la nube.
- Bloqueo entre procesos del mismo equipo para creación, publicación, recuperación, verificación, migración y limpieza. Durante la limpieza se bloquean las dos bóvedas. No coordina varios ordenadores ni sustituye la revisión de conflictos del cliente de nube.
- Lector independiente `recuperar_independiente.py`: implementación de lectura separada, sin importar `terabox_local` ni Qt; compatible con v1 y v2. Necesita Python y PyNaCl. No incorpora recuperación de contraseñas.
- Vectores públicos exclusivamente sintéticos de v1 y v2 en JSON y pruebas de lectura cruzada, corrupción, inventario, interrupción y exclusión entre procesos.
- Receta GitHub Actions para probar en Windows x64 y generar artefacto con SHA-256. El resultado remoto debe consultarse en Actions; la presencia del archivo no demuestra que esa ejecución haya pasado.

## Verificación local

31 pruebas aprobadas; última suite completa: 29,106 segundos, Windows 11 x64 / Python 3.14.6 / PyNaCl 1.6.2 / PySide6 6.10.2. Prueba streaming 80 MiB: pico de asignaciones Python 3,38 MiB; excluye memoria nativa, Qt y Argon2id. Se renderizó e inspeccionó la interfaz real con archivos sintéticos. La prueba del ejecutable final se registra en `prueba-exe-v2.json` cuando termina.

## Pendiente y límites

No se implementó detección de rollback de una copia completa válida: requiere una referencia confiable fuera de esa copia. El lector separado lo escribió el mismo proyecto; no constituye auditoría externa. El bloqueo entre procesos evita concurrencia cooperativa local, no ataques de otro proceso hostil que cambie rutas durante la operación. Faltan validación en PC limpio, volúmenes reales superiores a 50 GB, cortes reales de energía, arrastre físico con Explorer y auditoría independiente. Los ensayos de interrupción son simulaciones controladas.

Las carpetas virtuales dentro del repositorio cifrado siguen pendientes. El panel Desencriptados navega carpetas reales. No hay integración ni confirmación automática de nube. El binario no está firmado con certificado de editor: se distribuye un hash para identificarlo, no una firma de identidad. Ninguna de estas mejoras acredita cumplimiento clínico ni autoriza por sí sola el uso con pacientes.
