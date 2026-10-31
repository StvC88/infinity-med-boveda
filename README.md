# Infinity Med · Bóveda local v2.1

Aplicación portátil Windows x64 para cifrar archivos y nombres localmente, antes de que su cliente TeraBox u otra nube gestione la subida. El repositorio y su contraseña son independientes del ordenador y de esta interfaz. El motor usa PyNaCl/libsodium con Argon2id y XChaCha20-Poly1305 SecretStream; no implementa primitivas propias.

## Abrir el portable

Ejecute InfinityMedBoveda-v2.1.exe. Incluye Python y Qt; no requiere instalar Python. El propio programa se extrae temporalmente al arrancar, sin crear caché automática de documentos. No es una imagen de arranque USB y no está firmado con certificado de editor. Consulte verificacion-v2.1.json y SHA256-v2.1.txt para identificar la compilación probada.

## Uso

1. Abra la carpeta de repositorio y declare el área COMPLETA sincronizada por su nube. Para crear una bóveda use una carpeta vacía.
2. Elija una carpeta separada para temporales CIFRADOS, fuera de toda área de nube y en el mismo volumen que la bóveda. NTFS local es el entorno recomendado.
3. Cree el repositorio con una frase única de al menos 15 caracteres o desbloquee uno existente con su contraseña. La pista opcional se guarda legible: no revele la contraseña.
4. Arrastre archivos desde Windows a Encriptados o use Agregar. Se conservan sus originales. La lista cifrada es plana; todavía no admite importar jerarquías de carpetas.
5. Seleccione archivos y pulse la flecha para recuperar al DESTINO FINAL fuera de toda carpeta sincronizada. Sólo después de validar contenido, fin y tamaño se publican. Los nombres antiguos con controles bidireccionales se exportan mediante un alias seguro visible; el nombre autenticado se conserva en la bóveda. No sobrescribe archivos existentes. No hay caché adicional.
6. Desde Desencriptados puede navegar carpetas reales y copiar/arrastrar archivos individuales completos a Explorer. La exportación de carpetas está deshabilitada para no incluir parciales de operaciones descendientes. Desde Encriptados no se permite arrastrar hacia fuera. Recuperar es copiar: los archivos finales se conservan incluso al bloquear o cerrar.
7. Verificar repositorio autentica todo el contenido y el inventario sin escribir texto claro. La app no verifica la nube; muestra Guardado localmente, subida pendiente de comprobar. Usted comprueba el aviso de todos los archivos cargados en su cliente.

La interfaz oculta rutas completas salvo en su ayuda emergente. Bloquear oculta las vistas y limpia búsqueda/selección, pero los archivos ya recuperados siguen en su destino final y Python no garantiza borrar claves de RAM.

## Rotación y reemplazo

Rotar exige la contraseña actual y otra contraseña distinta. Crea una carpeta de bóveda nueva, clave independiente e inventario v2. Descifra/recifra por bloques en memoria, autentica cada original y vuelve a leer la copia nueva completa comparando nombres, tamaños y hashes de texto claro. No genera temporales descifrados durante migración.

Se conserva la bóveda anterior. Necesita espacio para ambas y un temporal cifrado del archivo mayor; el proceso puede tardar horas con terabytes. Una migración fallida queda marcada incompleta y no permite limpiar la anterior. No se reanuda automáticamente: repítala en otra carpeta vacía. Las pasadas de hash/verificación pueden mantener el último porcentaje aunque la interfaz siga respondiendo.

La limpieza automática de bóvedas anteriores está deshabilitada en esta versión, también desde el motor. Conserve la copia anterior; no existe un borrado alternativo oculto. La rotación y verificación siguen disponibles.

Los cambios/borrados pueden o no propagarse a la nube según el cliente. Versiones, papelera y otras copias antiguas pueden conservar datos accesibles con la contraseña anterior. No se afirma revocarlas ni purgarlas.

## Reinstalar o usar otro cliente

Conserve el repositorio completo: boveda.json, inventario.tbi (obligatorio en v2) y TODOS los .tbe. rotacion.tbr es un registro histórico de migración; no es necesario para descifrar y no activa ninguna limpieza en esta versión. Copie/descargue todo en el nuevo equipo, elija el repositorio y escriba su contraseña.

La contraseña sola no reconstruye archivos o encabezados borrados. No hay recuperación, restablecimiento, puerta trasera ni clave externa de recuperación. Si se pierde la contraseña y no queda acceso válido, los datos quedan inaccesibles.

El lector separado requiere Python y PyNaCl, sin Qt y sin importar el motor de la app:

```powershell
python -m pip install PyNaCl==1.6.2
python recuperar_independiente.py C:\Repositorio --output C:\Recuperados --cloud-root C:\AreaDeNube
```

Omitir --output verifica sin escribir texto claro. La contraseña se pide de forma interactiva; no se pasa por argumentos. FORMATO.md describe cómo desarrollar otro lector; vectores-publicos.json contiene únicamente datos y contraseñas SINTÉTICOS. La interoperabilidad comprobada es entre nuestro escritor y ese lector separado, no una auditoría externa.

## Integridad, interrupciones y recursos

Formato v1 anterior: sigue abriendo, pero sin inventario no puede detectar un archivo eliminado por completo. Migrar a una nueva bóveda crea v2. Los lectores antiguos que sólo admiten v1 no abren v2.

Formato v2: el inventario cifrado obligatorio detecta objetos faltantes/extra, cambios y eliminación del propio inventario. No detecta restaurar una copia antigua completa y válida: falta una referencia confiable externa para esa garantía.

Cada objeto se cifra en bloques de 1 MiB con RAM de contenido acotada; Argon2id usa además 64 MiB y Qt tiene su consumo. Hasta 10000 archivos por bóveda; inventario máximo 2 MiB. Se publica por renombrado local en el mismo volumen, después de fsync, sin sobrescritura. Los temporales cifrados quedan fuera del área declarada. La actualización de objeto e inventario son dos publicaciones: un corte puede dejar un objeto completo sin registrar. Se detecta, se conserva y se bloquean importaciones; puede recuperarse individualmente. No hay reparación automática ni garantía de transacción remota.

La recuperación usa un .partial de operación en el destino final. Ante error/cancelación normal se elimina. Un cierre forzado puede dejar texto claro. La interfaz registra las rutas e identidades de sus propios parciales en %LOCALAPPDATA%\InfinityMedBoveda\recuperaciones.json, sin contenido ni claves. Revisar recuperaciones incompletas muestra las rutas y solicita eliminación explícita. Sólo elimina objetos registrados con identidad comprobada sobre el archivo abierto y rechaza operaciones activas; no busca ni borra archivos por extensión. Los parciales de versiones antiguas o del lector independiente no están registrados. No hay borrado forense; un directorio temporal normal no es memoria volátil. El registro contiene rutas potencialmente sensibles: proteja también el perfil local y el destino.

En Windows, el origen se abre con compartición de sólo lectura para impedir escritores compatibles con las reglas de Windows mientras dura la importación. Un conflicto permite reintentar. No se garantiza un snapshot frente a mappings previos, drivers o un sistema comprometido. El bloqueo entre procesos coordina sólo este equipo. Rechaza enlaces/junctions existentes; no constituye una garantía general contra cualquier atacante local con control de las rutas. No modifique repositorios durante operaciones.

La creación y rotación rechazan patrones obvios y términos previsibles del producto mediante una lista local limitada. No es un corpus exhaustivo de contraseñas filtradas ni una garantía de entropía. No se envían contraseñas a servicios externos. Las bóvedas antiguas siguen abriendo con su codificación original y se advierte si su contraseña es débil. Los límites de intentos de una interfaz no frenan ataques offline sobre una copia. Los nuevos nombres con controles bidireccionales se rechazan; los antiguos se muestran con escapes visibles y se recuperan con alias seguros, sin normalización Unicode silenciosa.

Los cifrados deben estar accesibles localmente. No hay descarga automática propia, API ni credenciales de nube. Si el cliente hidrata archivos al leerlos, las esperas/errores quedan a cargo de Windows y pueden retrasar la cancelación. Si un archivo sólo está en nube y no se ve localmente, la app no lo conoce. Compruebe límites de tamaño por objeto y cuota de su proveedor: el cifrado por bloques no divide un archivo grande en objetos pequeños de nube.

## Desarrollo y construcción

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe terabox_local.py
.\.venv\Scripts\python.exe -m unittest -v test_vault test_ui test_improvements test_password_security test_release_security
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

build.ps1 crea un entorno local aislado; BovedaLocal.spec incluye assets y el backend cffi. El flujo de GitHub Actions prueba y construye en Windows. Consulte sus ejecuciones para conocer el estado remoto; el archivo de configuración no acredita por sí solo una ejecución aprobada. Licencias de dependencias y procedencia del logo están incluidas. El logo es una adaptación del material suministrado, no el original vectorial.

## Estado y límites

Consulte CAMBIOS-v2.1.md y VERIFICACION-v2.1.md. No probado en PC limpio, TeraBox real, volúmenes superiores a 50 GB ni cortes físicos de energía. Las pruebas de interfaz no sustituyen un arrastre físico completo con Explorer. No tiene auditoría independiente ni certificación clínica. La confidencialidad de documentos recuperados depende también del equipo, de las personas autorizadas y de sus respaldos. Android/iOS y unidad virtual quedan fuera de esta fase.
