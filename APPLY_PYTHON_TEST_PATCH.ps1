# Run this script from the extracted patch directory. Never changes datasets,
# virtual environments, existing active ml/heads, or database credentials.
param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

# SHA-256 of the exact files in CodeAuthentic_Source_For_Review(2).zip.
# Refuse to overwrite if the actual project has moved on since that review.
$expected = [ordered]@{
    'ml\predictor.py' = '59BA150048FF4613997E9CC1E2118326493AF3AFC8F474E92EAD96864C6AB28F'
    'src\utils\api.ts' = '772DF41DDC4F9C48C80C1CFD88D097FC8F81C1156EBD97C07F6C3EDD4426CD13'
    'src\components\InstructorDashboard.tsx' = '13BB091BBE7073A2BBA53105430F7E11D5660224AAE2F17B5FEE580C70266E90'
}
$sourceCandidates = [ordered]@{
    'ml\candidates\python.joblib' = '762FEB11D7CF735995E8DC1B54D3D6EF62D3E97DE0E7637355FA6603C6223C1C'
    'ml\candidates\python.json' = '8A755DC1DAE2B230784172347ECFB9271B414336CA889330676F16B860E80282'
}

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'START_SYSTEM.bat') -PathType Leaf)) {
    throw "ProjectRoot must point to the thesis folder containing START_SYSTEM.bat."
}
Write-Host "[CHECK] Project: $ProjectRoot"
foreach ($rel in $expected.Keys) {
    $target = Join-Path $ProjectRoot $rel
    $source = Join-Path $PSScriptRoot $rel
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Patch is missing $rel" }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Existing project is missing $rel" }
    $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
    if ($hash -ne $expected[$rel]) {
        throw "STOPPED SAFELY: $rel differs from the uploaded review ZIP. No files were changed. Ask for an updated patch instead of overwriting newer work."
    }
}
foreach ($rel in $sourceCandidates.Keys) {
    $source = Join-Path $PSScriptRoot $rel
    $target = Join-Path $ProjectRoot $rel
    if (-not (Test-Path -LiteralPath $source -PathType Leaf) -or
       (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $sourceCandidates[$rel]) {
        throw "Candidate checksum mismatch in patch: $rel"
    }
    if (Test-Path -LiteralPath $target -PathType Leaf) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $sourceCandidates[$rel]) {
            throw "STOPPED SAFELY: Existing $rel differs from this reviewed candidate. No files were changed."
        }
    }
}

$backup = Join-Path $ProjectRoot ("_python_test_patch_backup_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($rel in $expected.Keys) {
    $dest = Join-Path $backup $rel
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $rel) -Destination $dest -ErrorAction Stop
}
Write-Host "[BACKUP] Original source saved at $backup"

try {
    foreach ($rel in $expected.Keys) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $rel) -Destination (Join-Path $ProjectRoot $rel) -Force
    }
    foreach ($rel in $sourceCandidates.Keys) {
        $dest = Join-Path $ProjectRoot $rel
        if (-not (Test-Path -LiteralPath $dest -PathType Leaf)) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot $rel) -Destination $dest
        }
    }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'START_PYTHON_TEST_MODE.bat') -Destination (Join-Path $ProjectRoot 'START_PYTHON_TEST_MODE.bat') -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PYTHON_CODEBERT_TEST_MODE_README.md') -Destination (Join-Path $ProjectRoot 'PYTHON_CODEBERT_TEST_MODE_README.md') -Force
    $testDest = Join-Path $ProjectRoot 'tests'
    New-Item -ItemType Directory -Path $testDest -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'tests\test_python_test_mode.py') -Destination (Join-Path $testDest 'test_python_test_mode.py') -Force
} catch {
    foreach ($rel in $expected.Keys) {
        Copy-Item -LiteralPath (Join-Path $backup $rel) -Destination (Join-Path $ProjectRoot $rel) -Force
    }
    throw "Copy failed; original three source files restored. Details: $_"
}

Write-Host ''
Write-Host '[SUCCESS] Python CodeBERT test mode integrated. Existing .env, DB, dataset, active heads and Java training files were not changed.' -ForegroundColor Green
Write-Host 'Run START_PYTHON_TEST_MODE.bat (not START_SYSTEM.bat) for local experimental inference.'
Write-Host "Source backup: $backup"
