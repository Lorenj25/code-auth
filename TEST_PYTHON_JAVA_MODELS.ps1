param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw "Virtual environment Python not found: $python" }
$script = Join-Path $PSScriptRoot 'INTEGRATE_PYTHON_JAVA.py'
& $python $script --project-root $root --action test
if ($LASTEXITCODE -ne 0) { throw 'Smoke test failed. Please copy the error output for diagnosis.' }
