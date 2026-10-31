# Formato interoperable v1

La aplicación es un cliente del repositorio, no una llave vinculada al ordenador. Una copia completa del repositorio y su contraseña permiten desbloquearlo desde otra instalación. No hay secretos en el registro de Windows, identificador de equipo, servidor o licencia. Si se borran todas las copias del repositorio, la contraseña no reconstruye los datos.

Implementación de referencia: `terabox_local.py`. Una aplicación independiente debe implementar exactamente este formato; no basta con usar cualquier cifrado y la misma contraseña. La interoperabilidad con un segundo motor independiente todavía no se ha probado.

## Encabezado

`boveda.json`: JSON UTF-8, máximo 8192 bytes. Campos obligatorios: version=1, vault (32 caracteres hexadecimales minúsculos), salt (16 bytes), ops=3, mem=67108864, hint (hasta 300 caracteres), state, nonce (24 bytes), wrapped (48 bytes). Los campos binarios usan Base64 estándar con relleno. Estados admitidos: ready, migration-incomplete, migration-complete.

Contraseña: UTF-8 sin normalización Unicode; de 1 a 1024 bytes. Argon2id de libsodium, salida de 32 bytes, opslimit=3, memlimit=64 MiB. Esa clave descifra wrapped mediante XChaCha20-Poly1305-IETF. El resultado es la clave de datos de 32 bytes.

Datos adicionales del envoltorio: objeto del encabezado sin nonce ni wrapped, serializado como `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')`. Las claves se ordenan; no se añaden espacios ni salto final. La pista y el estado quedan autenticados. Valide estructura y límites antes de derivar claves.

## Objetos

Cada archivo usa un nombre aleatorio de 32 hexadecimales minúsculos más `.tbe`. Su contenido comienza por 8 bytes ASCII `TBLOCAL1`, 16 bytes de identidad de bóveda y 16 bytes de identidad de archivo, ambos decodificados desde hexadecimal. Estos 40 bytes son los datos adicionales de TODOS los mensajes SecretStream. Deben coincidir con el encabezado y el nombre del objeto. Siguen 24 bytes de encabezado SecretStream XChaCha20-Poly1305.

Cada trama es longitud uint32 big-endian seguida del mensaje cifrado. SecretStream añade 17 bytes a cada mensaje. Primera trama: metadatos JSON UTF-8 {name,size}, etiqueta MESSAGE, máximo 4096 bytes de texto claro. name es sólo nombre base seguro de Windows, sin rutas; size es entero entre 0 y 2^63−1. Las siguientes tramas tienen etiqueta MESSAGE y de 1 a 1048576 bytes de texto claro. La última tiene etiqueta FINAL y texto claro vacío. Incluso un archivo vacío requiere metadatos y FINAL. Rechace cualquier byte posterior, tamaño total distinto, etiqueta inesperada o error de autenticación. No publique un descifrado hasta validar FINAL y EOF.

Los nombres originales sólo están dentro del primer mensaje cifrado. Los nombres físicos, cantidades, tamaños aproximados y fechas no se ocultan. No hay directorios virtuales en v1.

## Rotación

La rotación crea otra bóveda y otra clave aleatoria; vuelve a cifrar cada archivo y verifica la copia completa. La copia anterior sigue admitiendo la contraseña anterior. `rotacion.tbr` es opcional para leer archivos: contiene nonce de 24 bytes y un JSON cifrado mediante XChaCha20-Poly1305-IETF con la clave de datos nueva y la identidad binaria de bóveda como datos adicionales. Es un registro para limpieza local, no una clave de recuperación. Un cliente alternativo puede ignorarlo para recuperar contenido; no debe ejecutar sus instrucciones de borrado sin implementar todas las validaciones.

## Restauración en otro equipo

Conserve boveda.json y TODOS los .tbe, descargue la copia completa, instale un cliente compatible, seleccione el repositorio y escriba su contraseña. La contraseña abre el repositorio, no una cuenta de la aplicación. No publique datos ni encabezados reales en GitHub. Nunca transforme el formato silenciosamente; una modificación incompatible requiere una versión nueva y un migrador explícito.
