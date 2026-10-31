# Formato de repositorio v1 y v2

La aplicación es un cliente del repositorio, no una llave vinculada al ordenador. Una copia completa del repositorio y su contraseña permiten desbloquearlo desde otra instalación. No hay secretos en el registro de Windows, identificador de equipo, servidor o licencia. Si se borran todas las copias del repositorio, la contraseña no reconstruye los datos.

Implementación de referencia: `terabox_local.py`. Una aplicación independiente debe implementar exactamente este formato; no basta con usar cualquier cifrado y la misma contraseña. Se prueba la lectura con recuperar_independiente.py, que no importa el motor ni Qt; esto no equivale a una auditoría externa ni a probar otro escritor.

## Encabezado

`boveda.json`: JSON UTF-8, máximo 8192 bytes. Campos obligatorios: version=1, vault (32 caracteres hexadecimales minúsculos), salt (16 bytes), ops=3, mem=67108864, hint (hasta 300 caracteres), state, nonce (24 bytes), wrapped (48 bytes). Los campos binarios usan Base64 estándar con relleno. Estados admitidos: ready, migration-incomplete, migration-complete.

Codificación para desbloquear: UTF-8 sin normalización Unicode; de 1 a 1024 bytes. La política de creación/rotación de v2.1 exige al menos 15 caracteres y rechaza algunos patrones locales; no cambia la codificación ni impide leer contraseñas antiguas. Argon2id de libsodium, salida de 32 bytes, opslimit=3, memlimit=64 MiB. Esa clave descifra wrapped mediante XChaCha20-Poly1305-IETF. El resultado es la clave de datos de 32 bytes.

Datos adicionales del envoltorio: objeto del encabezado sin nonce ni wrapped, serializado como `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')`. Las claves se ordenan; no se añaden espacios ni salto final. La pista y el estado quedan autenticados. Valide estructura y límites antes de derivar claves.

## Objetos

Cada archivo usa un nombre aleatorio de 32 hexadecimales minúsculos más `.tbe`. Su contenido comienza por 8 bytes ASCII `TBLOCAL1`, 16 bytes de identidad de bóveda y 16 bytes de identidad de archivo, ambos decodificados desde hexadecimal. Estos 40 bytes son los datos adicionales de TODOS los mensajes SecretStream. Deben coincidir con el encabezado y el nombre del objeto. Siguen 24 bytes de encabezado SecretStream XChaCha20-Poly1305.

Cada trama es longitud uint32 big-endian seguida del mensaje cifrado. SecretStream añade 17 bytes a cada mensaje. Primera trama: metadatos JSON UTF-8 {name,size}, etiqueta MESSAGE, máximo 4096 bytes de texto claro. name es sólo nombre base seguro de Windows, sin rutas; size es entero entre 0 y 2^63−1. Las siguientes tramas tienen etiqueta MESSAGE y de 1 a 1048576 bytes de texto claro. La última tiene etiqueta FINAL y texto claro vacío. Incluso un archivo vacío requiere metadatos y FINAL. Rechace cualquier byte posterior, tamaño total distinto, etiqueta inesperada o error de autenticación. No publique un descifrado hasta validar FINAL y EOF.

Los nombres originales sólo están dentro del primer mensaje cifrado. Los nombres físicos, cantidades, tamaños aproximados y fechas no se ocultan. No hay directorios virtuales en v1.

## Rotación

La rotación crea otra bóveda y otra clave aleatoria; vuelve a cifrar cada archivo y verifica la copia completa. La copia anterior sigue admitiendo la contraseña anterior. `rotacion.tbr` es opcional para leer archivos: contiene nonce de 24 bytes y un JSON cifrado mediante XChaCha20-Poly1305-IETF con la clave de datos nueva y la identidad binaria de bóveda como datos adicionales. Es un registro para limpieza local, no una clave de recuperación. Un cliente alternativo puede ignorarlo para recuperar contenido; no debe ejecutar sus instrucciones de borrado sin implementar todas las validaciones.

## Restauración en otro equipo

Conserve boveda.json y TODOS los .tbe, descargue la copia completa, instale un cliente compatible, seleccione el repositorio y escriba su contraseña. La contraseña abre el repositorio, no una cuenta de la aplicación. No publique datos ni encabezados reales en GitHub. Nunca transforme el formato silenciosamente; una modificación incompatible requiere una versión nueva y un migrador explícito.


## Extensión v2: inventario obligatorio

Los encabezados nuevos usan version=2 y un campo adicional inventory="v1", incluido en los datos adicionales autenticados del envoltorio. El resto de campos y los objetos .tbe conservan exactamente su codificación anterior. Los lectores antiguos que sólo admiten encabezados v1 deben rechazar v2. El cliente actual lee ambas versiones; no modifica una bóveda v1 al abrirla.

El archivo inventario.tbi es obligatorio en v2. Sus primeros 24 bytes son un nonce aleatorio; el resto es un objeto JSON UTF-8 cifrado con AEAD XChaCha20-Poly1305-IETF, clave de datos de la bóveda y AD igual a ASCII inventory-v1 concatenado con los 16 bytes de identidad de bóveda. El JSON mapea cada nombre de objeto .tbe a su SHA-256 hexadecimal minúsculo sobre TODOS los bytes cifrados de ese objeto. Se serializa con la misma función canónica del encabezado. Longitud total máxima: 2 MiB; máximo 10000 registros. No contiene nombres originales en texto claro.

La verificación exige que el conjunto físico de objetos coincida exactamente con el inventario y verifica carga completa, hash, FINAL y EOF. No detecta restaurar conjuntamente un inventario antiguo válido y sus objetos. Un cierre entre publicar el objeto y sustituir el inventario puede dejar un objeto extra íntegro: se conserva, no se admite como operación completada y se bloquean importaciones hasta revisión. La recuperación individual puede rescatarlo; no hay reparación automática.

El formato v1 sin inventario sigue recuperándose, pero no puede detectar un objeto eliminado en su totalidad. Migrarlo a una bóveda nueva crea v2 y una clave independiente. Conserve encabezado, inventario y todos los objetos al mover/restaurar v2.

recuperar_independiente.py es una segunda implementación de lectura de esta especificación. vectores-publicos.json transporta pequeños repositorios de prueba como pares nombre/base64, con contraseña y SHA-256 de texto claro publicados deliberadamente. Nunca usar sus contraseñas para datos reales. Las pruebas actuales validan el motor escritor contra ese lector, no una segunda implementación escritora ni una auditoría externa.

## Comportamiento de nombres y limpieza en la aplicación v2.1

El formato criptográfico permanece v1/v2. El nombre original autenticado no se normaliza ni se reescribe al abrir o rotar. La importación de nuevos archivos rechaza U+061C, U+200E, U+200F, U+202A–U+202E y U+2066–U+2069. Al mostrar nombres antiguos se usan escapes visibles [U+XXXX]. Ambos lectores exportan esos nombres con prefijo nombre-seguro- y escapes _UXXXX_; si excede 240 unidades UTF-16, emplean archivo-recuperado-<SHA256 del nombre UTF-8>.bin. Se rechazan colisiones sin sobrescribir. Los nombres internacionales legítimos sin esos controles se mantienen. Esta política de presentación/exportación es independiente del nombre autenticado.

La limpieza de bóvedas anteriores está deshabilitada incondicionalmente en v2.1. rotacion.tbr no autoriza borrados. El registro local de parciales de la interfaz no forma parte del repositorio, no contiene secretos de descifrado y no es necesario para restaurar en otro equipo.
