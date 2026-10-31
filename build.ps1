$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$buildWork = Join-Path $base 'work'
$envDir = Join-Path $buildWork 'build-venv'
New-Item -ItemType Directory -Force -Path $buildWork | Out-Null
py -3 -m venv $envDir
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python.' }
$pythonExe = Join-Path $envDir 'Scripts\python.exe'
& $pythonExe -c "import struct; assert struct.calcsize('P') == 8, 'Necesita Python x64'"
if ($LASTEXITCODE -ne 0) { throw 'Se necesita Python x64.' }
& $pythonExe -m pip install -r (Join-Path $base 'requirements.txt') PyInstaller==6.22.3 pyinstaller-hooks-contrib==2026.9
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
& $pythonExe -m PyInstaller --noconfirm --clean --distpath $base --workpath (Join-Path $buildWork 'build') (Join-Path $base 'BovedaLocal.spec')
if ($LASTEXITCODE -ne 0) { throw 'Falló la construcción del ejecutable.' }
Write-Host ('Ejecutable creado: ' + (Join-Path $base 'InfinityMedBoveda-v2.1.exe'))
