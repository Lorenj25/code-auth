param([Parameter(Mandatory = $true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path
$script = Join-Path $PSScriptRoot 'patch_logout_modal.py'
if (!(Test-Path -LiteralPath $script)) { throw 'Missing patch_logout_modal.py' }
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) { $python = $venvPython }
else { $python = 'python' }
& $python $script --project-root $root
if ($LASTEXITCODE -ne 0) { throw 'Logout patch stopped safely. Review message above.' }
