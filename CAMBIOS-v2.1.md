# Infinity Med Bóveda local 2.1

La versión 2.1 conserva el formato cifrado v1/v2 y la lectura de bóvedas existentes.

- Creación/rotación: mínimo 15 caracteres y rechazo local limitado de patrones previsibles. Desbloqueo compatible con contraseñas antiguas, con aviso cuando corresponde.
- Verificar comprueba también que el encabezado en disco coincide con el autenticado al abrir.
- Limpieza de bóvedas anteriores deshabilitada por completo; la rotación conserva ambas copias.
- Lectura de orígenes en Windows con compartición que rechaza escritura concurrente compatible con esos mecanismos.
- Nuevos nombres sin controles bidireccionales; nombres antiguos preservados internamente, visibles con escapes y exportados mediante alias seguros en ambos lectores.
- Exportación limitada a archivos completos individuales; carpetas navegables y parciales no exportables desde la interfaz.
- Registro local de parciales propios; revisión y eliminación explícita por identidad del archivo abierto cuando ya no hay operación activa.
- 50 pruebas automatizadas y prueba nativa del ejecutable final. GitHub Actions comprueba las cinco suites, construye y ejecuta la comprobación del binario.

No hay firma de editor confiable ni certificación clínica. SHA-256 identifica archivos, no acredita identidad del editor. La firma futura no garantiza ausencia inmediata de avisos SmartScreen. No se publican informes privados de auditoría ni demostraciones de explotación en este paquete.
