# Infinity Med — Bóveda local

Prototipo de escritorio que cifra archivos y nombres antes de colocarlos en una carpeta local gestionada por un proveedor de nube. Su objetivo es conservar el control de las claves y permitir la recuperación sin depender de una aplicación concreta, de una cuenta del desarrollador o del ordenador original.

La interfaz utiliza dos paneles: Encriptados y Desencriptados. Se importa desde Windows al panel encriptado; la flecha recupera al destino final elegido. Sólo el panel desencriptado permite exportar por arrastre. El diseño está evolucionando hacia un estilo zen, sin negritas. Se incorporó una adaptación del logo aportado por el usuario.

## Protecciones implementadas

PyNaCl/libsodium aporta Argon2id y XChaCha20-Poly1305 SecretStream; no se implementan primitivas propias. Hay autenticación por bloques y de fin, memoria de contenido acotada, nombres cifrados, publicación por archivo completo y validación de rutas. La rotación genera una clave independiente y verifica todos los archivos. La versión 2.1 conserva la bóveda anterior y deshabilita su limpieza automática.

Esto describe mecanismos concretos, no una garantía absoluta de seguridad. El formato es experimental y no tiene auditoría independiente. No se presenta como sistema clínico certificado ni como prueba de cumplimiento normativo. El uso con datos de pacientes exige evaluar acceso al equipo, copias de seguridad, texto claro recuperado, usuarios autorizados y requisitos aplicables antes de desplegarlo. Este repositorio debe contener exclusivamente código, documentación y pruebas sintéticas.

## Independencia del cliente

Puede reinstalar la aplicación o desarrollar otra compatible y abrir el repositorio con su contraseña. Debe conservar el repositorio completo, incluido boveda.json. Sin datos o sin encabezado no existe recuperación por contraseña. No hay restablecimiento, puerta trasera ni clave externa de recuperación. Consulte FORMATO.md para implementar un lector independiente.

## Estado

Prototipo, no producto clínico terminado. El motor tiene pruebas automatizadas; la nueva interfaz está en revisión. La jerarquía de carpetas cifradas no está implementada. No hay confirmación automática de subida a TeraBox ni descargas propias: el cliente de nube es independiente. Los ejecutables anteriores no representan necesariamente los últimos cambios de interfaz.

Consulte CAMBIOS-v2.1.md para inventario autenticado, lector independiente y estado de pruebas. Consulte README.md para ejecutar desde Python, FORMATO.md para interoperabilidad y VERIFICACION-v2.1.md para el alcance de las pruebas de la compilación actual. Las afirmaciones de pruebas corresponden a las versiones descritas allí, no a una auditoría del producto.
