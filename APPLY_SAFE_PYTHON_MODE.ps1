param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Could not locate the project .venv Python. Activate/create the project virtual environment before installing.'
}
& $python (Join-Path $PSScriptRoot 'APPLY_COMPATIBLE_PYTHON_MODE.py') --project $root
if ($LASTEXITCODE -ne 0) { throw 'Installer stopped safely. Do not force the update; request a review of your current predictor.py.' }
