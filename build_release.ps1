$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install -q -r requirements.txt pyinstaller
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }

python -m PyInstaller --noconfirm throwing_scale.spec

$outDir = Join-Path $PSScriptRoot "release"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Copy-Item -Force (Join-Path $PSScriptRoot "data\presets.json") (Join-Path $PSScriptRoot "dist\ThrowingDistanceScale\data\presets.json")

$zip = Join-Path $outDir "ThrowingDistanceScale-windows-x64.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $PSScriptRoot "dist\ThrowingDistanceScale\*") -DestinationPath $zip
Write-Host "built $zip"
