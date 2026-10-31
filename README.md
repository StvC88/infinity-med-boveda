# Infinity Med — Bóveda local

Prototipo de escritorio que cifra archivos y nombres antes de colocarlos en una carpeta local gestionada por un proveedor de nube. Su objetivo es conservar el control de las claves y permitir la recuperación sin depender de una aplicación concreta, de una cuenta del desarrollador o del ordenador original.

La interfaz utiliza dos paneles: Encriptados y Desencriptados. Se importa desde Windows al panel encriptado; la flecha recupera al destino final elegido. Sólo el panel desencriptado permite exportar por arrastre. El diseño está evolucionando hacia un estilo zen, sin negritas. El logo oficial está pendiente de incorporación.

## Protecciones implementadas

PyNaCl/libsodium aporta Argon2id y XChaCha20-Poly1305 SecretStream; no se implementan primitivas propias. Hay autenticación por bloques y de fin, memoria de contenido acotada, nombres cifrados, publicación por archivo completo y validación de rutas. La rotación genera una clave independiente y verifica todos los archivos antes de permitir limpiar la versión anterior.

Esto describe mecanismos concretos, no una garantía absoluta de seguridad. El formato es experimental y no tiene auditoría independiente. No se presenta como sistema clínico certificado ni como prueba de cumplimiento normativo. El uso con datos de pacientes exige evaluar acceso al equipo, copias de seguridad, texto claro recuperado, usuarios autorizados y requisitos aplicables antes de desplegarlo. Este repositorio debe contener exclusivamente código, documentación y pruebas sintéticas.

## Independencia del cliente

Puede reinstalar la aplicación o desarrollar otra compatible y abrir el repositorio con su contraseña. Debe conservar el repositorio completo, incluido boveda.json. Sin datos o sin encabezado no existe recuperación por contraseña. No hay restablecimiento, puerta trasera ni clave externa de recuperación. Consulte FORMATO.md para implementar un lector independiente.

## Estado

Prototipo, no producto clínico terminado. El motor tiene pruebas automatizadas; la nueva interfaz está en revisión. La jerarquía de carpetas cifradas no está implementada. No hay confirmación automática de subida a TeraBox ni descargas propias: el cliente de nube es independiente. Los ejecutables anteriores no representan necesariamente los últimos cambios de interfaz.

Consulte README.md para ejecutar desde Python, FORMATO.md para interoperabilidad y VERIFICACION.md para el alcance histórico de las pruebas. Las afirmaciones de pruebas corresponden a las versiones descritas allí, no a una auditoría del producto.


## Instrucciones de ejecución

# Bóveda local — prototipo Windows x64

Cifra contenido y nombres **en este ordenador**, antes de que su cliente TeraBox u otra nube suba los archivos. No conecta con cuentas, no usa credenciales ni API de nube y no automatiza navegadores. No modifica ni elimina los originales que se importan.

## Inicio sin instalar

Ejecute `BovedaLocal.exe`. Es un ejecutable portátil único para Windows x64 que incluye Python y las bibliotecas necesarias; no requiere instalar Python en el equipo destino. Se construyó en Windows 11 x64. Al arrancar extrae componentes del programa a una carpeta temporal del sistema; eso no es una caché de documentos descifrados. No está firmado digitalmente. No se ha probado en un PC limpio ni en todas las versiones de Windows.

Mantenga todos estos entregables y las licencias si redistribuye el prototipo. Para cambiar o sustituir sus bibliotecas, se incluye el código y `build.ps1`.

## Primer uso

1. Cree tres carpetas separadas: una **bóveda vacía** que su cliente de nube pueda subir, una carpeta para **temporales cifrados** fuera de toda área de nube y una carpeta de **recuperación** también fuera de toda área de nube. Bóveda y temporales cifrados deben estar en el mismo volumen; se recomienda NTFS local.
2. Pulse **Abrir carpeta cifrada**. Elija la bóveda y después declare el **área completa que sincroniza su cliente**: puede ser la misma carpeta o una carpeta superior. La app rechazará originales, temporales y recuperaciones dentro del área declarada. No puede descubrir automáticamente todas las carpetas sincronizadas por todos sus clientes: declárela correctamente y no elija otra área de nube como destino de texto claro.
3. Elija **Carpeta temporal cifrada** y pulse **Crear bóveda**. Introduzca y repita una contraseña larga y única. La pista opcional se guarda **legible** y es visible antes del desbloqueo: no debe revelar la contraseña. No guarde una copia de la contraseña en la pista.
4. Use **Agregar archivos** o arrastre archivos desde Explorer/escritorio a la lista. Sólo se aceptan archivos regulares; las carpetas completas y jerarquías de subcarpetas aún no están implementadas. El listado es plano, ordenado por nombre, con búsqueda y menú contextual.
5. La app indica **Guardado localmente; subida pendiente de comprobar en su cliente de nube**. Mantenga su cliente ejecutándose y compruebe su aviso de carga completa. Guardar en una carpeta local NO demuestra que se haya subido.

Los nombres originales sólo aparecen al desbloquear. Los nombres de los archivos almacenados son identificadores aleatorios. Se revelan tamaños aproximados, cantidad de archivos, momentos de modificación y pista pública. El listado autentica los metadatos de cada archivo, no toda su carga; la recuperación comprueba el archivo entero.

## Recuperar, copiar y arrastrar hacia Windows

1. Abra la bóveda, declare su área de nube y pulse **Desbloquear**. Seleccione uno o varios archivos.
2. Pulse **Recuperar / Preparar para copiar** y elija el **destino final**, fuera de toda carpeta sincronizada. El estado pasa por preparación/descifrado y muestra progreso. Para 50 GB necesita espacio para el archivo completo y tiempo para leerlo, verificarlo y escribirlo.
3. El programa escribe por bloques en un `.partial` de operación al lado del destino final. Sólo tras autenticar todos los bloques, el marcador de fin y la ausencia de datos adicionales lo publica con el nombre original. No sobrescribe archivos existentes. Ante error/cancelación ordinaria elimina el parcial; si se termina el proceso a la fuerza o se corta la energía, puede quedar un `.partial` que contiene texto claro y debe eliminar manualmente. No es un archivo recuperado válido.
4. Cuando aparezca **Listo para copiar**, el archivo **ya está recuperado en su destino final**. Puede conservarlo allí, pulsar **Copiar archivos** y pegar en Explorer, o arrastrar desde la lista hacia Explorer/escritorio. La app entrega archivos reales, no sólo texto con rutas. El arrastre es una copia; no se eliminan los recuperados. Mantenga abierta la app hasta terminar el pegado.

No se crea una caché automática adicional y no se borran automáticamente las recuperaciones del usuario. Cambiar de selección o bloquear la bóveda no borra archivos ya recuperados. Si recuperó algunos archivos antes de una cancelación, éstos se conservan; vuelva a seleccionar sólo los que falten.

Arrastrar directamente un `.tbe` desde la carpeta cifrada de Explorer no lo descifra. Debe usar nuestra lista desbloqueada y preparar primero la recuperación. La integración nativa de arrastre y portapapeles está implementada con Qt, pero la interacción física con Explorer y otras aplicaciones aún necesita validación manual.

## Qué hace y qué no hace TeraBox

La app sólo lee cifrados que Windows puede abrir en una carpeta local. No implementa descarga bajo demanda, proveedor virtual ni montaje de unidad. Si su proveedor hidrata un archivo al leerlo, la lectura ocurre en segundo plano y puede esperar o fallar; este comportamiento no está verificado con TeraBox. Un bloqueo de lectura del proveedor puede demorar la cancelación hasta que Windows devuelva el control.

Cuando los cifrados no estén accesibles, descárguelos/sincronícelos con su cliente y actualice la lista. Si un archivo sólo existe en la nube y no aparece localmente, la app no conoce su existencia ni puede listar su nombre. Conserve y descargue también `boveda.json`: sin ese encabezado no podrá acceder a los datos.

La [guía oficial de TeraBox](https://blog.terabox.com/how-to-upload-photos-to-terabox/) describe carga manual y respaldo de carpetas en Windows. En una consulta acotada al 31 de octubre de 2026 no se verificó una interfaz pública soportada del cliente local para certificar el fin de una subida. **La verificación automática de nube queda pendiente**. No se ha comprobado que la configuración concreta de su cliente suba cualquier carpeta elegida, ni que propague borrados. Cada otro proveedor necesitaría su propia comprobación. Los límites por archivo/cuota del proveedor también se aplican: este prototipo produce un cifrado por archivo, no divide un archivo grande en objetos de nube más pequeños.

## Rotar contraseña Y clave de datos

**Rotar a una bóveda nueva** exige escribir la contraseña actual, incluso si está desbloqueada. Solicita una contraseña distinta, nueva pista y otra carpeta vacía y separada. Si esa carpeta está en otra área de nube, declárela correctamente al volver a abrirla; durante la operación no se genera texto claro en disco.

Se genera una clave de datos aleatoria independiente. Cada archivo se descifra y vuelve a cifrar en memoria en bloques de 1 MiB. Se autentica íntegramente el original antes de publicar cada archivo nuevo. Después se desbloquea la nueva bóveda con la contraseña nueva y **se lee y autentica TODO su contenido**, comparando nombres, tamaños y SHA-256 del texto claro con la lectura de los originales. Sólo entonces se publica un registro autenticado de rotación y el estado `migration-complete`.

Necesita espacio para coexistir ambas bóvedas más un temporal cifrado del tamaño del archivo mayor. La comprobación completa añade lecturas de disco; una rotación de terabytes puede tardar horas. Hay progreso durante el recifrado; las pasadas de verificación/hash pueden mantener el último porcentaje mientras la interfaz sigue respondiendo y permite cancelar.

La bóveda anterior se conserva y sigue accesible con su contraseña anterior. Una interrupción deja la nueva con estado `migration-incomplete` y sólo los archivos completados; no habilita limpieza. Se pueden recuperar esos archivos, pero no se reanuda la migración automáticamente: repítala en otra carpeta vacía. No use una bóveda incompleta como sustituto de la anterior.

### Reemplazo y limpieza de la versión anterior

1. Compruebe que la **nueva carpeta completa** está incluida en la configuración de carga del cliente. Espere el aviso que usted observa de **todos los archivos cargados** en TeraBox.
2. En la bóveda nueva pulse **Limpiar versión anterior**. Confirme expresamente que verificó esa subida y escriba la contraseña nueva. La aplicación registra su confirmación para esta operación; no lee el aviso ni afirma haber verificado la nube.
3. Antes de borrar nada vuelve a verificar TODOS los archivos nuevos contra el registro autenticado de migración. Verifica también el encabezado anterior y los hashes de los cifrados antiguos que sigan presentes.
4. Sólo elimina los cifrados antiguos enumerados y coincidentes, uno por uno. Elimina el encabezado antiguo al final únicamente si no quedan entradas cifradas en esa carpeta. Nunca borra carpetas recursivamente, originales importados ni archivos ajenos. Si interrumpe la limpieza, la nueva copia completa permanece; puede repetir la limpieza para los archivos antiguos restantes. La carpeta anterior queda existente.

No añada archivos ni modifique las bóvedas entre rotación y limpieza: la verificación bloquea la limpieza si cambió el conjunto nuevo. Conserve `rotacion.tbr` en la bóveda nueva si necesita limpiar después. El registro está cifrado e incluye la ruta local anterior; no contiene una copia de su clave anterior.

Eliminar localmente puede o no propagarse: depende del cliente, y un respaldo de sólo subida puede conservar los antiguos en la nube. Papelera, historial de versiones, otras copias y claves previamente expuestas no se revocan ni se purgan. **Las copias de la bóveda antigua siguen admitiendo la contraseña antigua.** La rotación no puede invalidarlas. Este prototipo rota realmente la clave y los archivos, no sólo la envoltura de la misma clave.

## Seguridad y formato

- [PyNaCl 1.6.2](https://pynacl.readthedocs.io/en/latest/) / libsodium. Contenido y metadatos con [XChaCha20-Poly1305 SecretStream](https://doc.libsodium.org/secret-key_cryptography/secretstream). Bloques con longitudes acotadas, fin autenticado obligatorio y rechazo de bytes posteriores, alteración, truncado y reordenación.
- Contraseña derivada con Argon2id: 3 operaciones, 64 MiB y sal aleatoria. Clave de datos aleatoria de 32 bytes envuelta con AEAD XChaCha20-Poly1305. Parámetros y tamaño del encabezado se validan antes de derivar/reservar recursos. No se guarda contraseña ni clave de datos en texto claro en disco.
- Formato propio **experimental** versionado: `boveda.json`, objetos aleatorios `.tbe` y registro opcional cifrado `rotacion.tbr`. Cada objeto liga su versión, identidad de bóveda y de archivo mediante datos autenticados. Un objeto grande no obliga a reescribir los demás.
- Temporales cifrados fuera del área declarada. En Windows se publican mediante renombrado en el mismo volumen, sin sobrescribir, después de vaciar buffers y sincronizar el archivo. No se copia un archivo parcial a la carpeta de nube. En otros sistemas el motor usa enlace duro y no se ha validado esta aplicación allí.
- Rechaza rutas absolutas/traversal, separadores, ADS, controles, nombres reservados Windows y enlaces/junctions existentes. Use volúmenes locales y un equipo confiable. No hay defensa contra otro proceso hostil del mismo usuario que cambie directorios entre comprobación y apertura; no ejecute dos instancias sobre una misma bóveda ni la modifique durante operaciones.
- Bloques de 1 MiB con memoria de contenido acotada; Argon2id usa además 64 MiB y Qt tiene su propio consumo. Hasta **10 000 archivos por bóveda** en este prototipo; índices y registro crecen con ese número. El registro de rotación está limitado a 32 MiB. Los tamaños usan enteros de 64 bits hasta 2^63−1; los límites reales del disco/nube son independientes.
- No hay recuperación, restablecimiento, puerta trasera, clave maestra externa ni clave de recuperación. **Si olvida la contraseña y no conserva acceso válido, los datos quedan inaccesibles.** Perder el encabezado también impide abrirlos. Conserve copias completas de la bóveda y su contraseña mediante su propio procedimiento.
- Bloquear retira las referencias activas y la lista, pero Python no garantiza borrar claves de RAM. No protege contra malware, capturas de pantalla, archivos de paginación ni otros usuarios con acceso al texto claro recuperado. No hay borrado forense, auditoría criptográfica independiente, protección contra restaurar versiones antiguas válidas ni detección de archivos que alguien elimine por completo de una bóveda corriente.

## Ejecutar desde Python en Windows

Instale Python x64 3.11 o posterior con Qt compatible. Abra PowerShell en esta carpeta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe terabox_local.py
```

`terabox_local.py` es el punto de entrada y motor; necesita `qt_ui.py` al lado para la interfaz.

Pruebas con datos sintéticos, sin cuenta TeraBox:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_vault test_ui
```

Para volver a crear el ejecutable desde Windows x64 con Python instalado:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

El script crea un entorno aislado local e instala versiones fijadas. No instala servicios ni modifica Python global. El resultado es `BovedaLocal.exe`. [PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html) incluye el intérprete y dependencias en el ejecutable.

Consulte `VERIFICACION.md` para resultados exactos y límites de las pruebas. Android/iOS y unidad virtual quedan fuera de esta fase.
