param([Parameter(Mandatory = $true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path
$pyScript = Join-Path $PSScriptRoot 'RESTORE_PREMIUM_UI.py'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) { $python = $venvPython } else { $python = 'python' }
& $python $pyScript --project-root $root
if ($LASTEXITCODE -ne 0) { throw 'Recovery stopped safely; no changes to unknown UI files.' }
