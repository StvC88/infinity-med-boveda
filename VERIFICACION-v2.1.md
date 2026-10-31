# Verificación de la compilación 2.1

Fecha: 2026-10-31. Plataforma probada: Windows x64 del entorno de desarrollo, con datos sintéticos. No es una certificación de seguridad ni autorización para datos de pacientes.

La compilación InfinityMedBoveda-v2.1.exe se construyó después de las correcciones mediante PyInstaller. verificacion-v2.1.json liga su SHA-256 a los hashes de fuente y resultados; SHA256-v2.1.txt permite identificarla. No se reutiliza el informe de los ejecutables anteriores.

Se ejecutaron 50 pruebas de las cinco suites: 50 aprobadas, sin errores ni omisiones, en 31.737 segundos. El registro completo está en pruebas-v2.1.txt. Incluyen compatibilidad, manipulación de encabezado/contenido, contraseñas, nombres internacionales y bidireccionales, colisiones de exportación, escritura concurrente nativa de Windows, directorios no exportables y recuperación de parciales registrados tras terminación abrupta de un proceso real. El ensayo de 80 MiB midió 3.51 MiB de asignaciones Python; excluye Qt, Argon2 y otra memoria nativa.

El ejecutable final completó la comprobación nativa con interfaz iniciada, proceso de 64 bits, cifrado/recuperación y rotación completos, conservación de la copia anterior y limpieza deshabilitada. No sólo se comprobó el código Python.

La limpieza antigua se cierra mediante deshabilitación, no mediante una afirmación de borrado seguro. Los controles de nombres, encabezado, exportación individual y compartición Windows están implementados y tienen regresiones. El texto claro parcial tras cierre forzado sigue siendo un riesgo conocido: se registra y ofrece revisión explícita; no se promete eliminación automática ni forense. Tampoco se promete zeroization en Python, protección general frente a un equipo comprometido ni detección de rollback completo.

Pendiente de cobertura: creación de symlinks en un entorno que ya permita esa operación (el equipo actual devuelve WinError 1314); restauración en otro PC limpio; arrastre físico completo entre la aplicación y Explorer; TeraBox real, archivos/volúmenes grandes y cortes físicos de energía. No se cambiaron políticas de seguridad del equipo para completar esas pruebas. La configuración CI se publica, pero una ejecución remota debe consultarse por su revisión y no se da por aprobada por existir el archivo.

Se intentó un ensayo adicional con la interfaz real de fuente y datos sintéticos: selección y botón Copiar archivos confirmados por el estado Listo para pegar en Explorer. No se pudo confirmar navegación/pegado en la ventana de Explorer mediante el control de escritorio disponible. Se registra como ensayo inconcluso, sin atribuirlo a una aprobación de integración ni del arrastre.

Distribución pública: falta firma con identidad de editor confiable y gestión protegida de sus secretos. No se generó una clave improvisada. SHA-256 no sustituye firma; firmar no garantiza eliminar inmediatamente avisos SmartScreen. Los informes privados y PoCs se conservan fuera del paquete y del envío a GitHub.
