param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$patchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path

# Built specifically for the completed Mobile UI + Premium Navbar versions.
# Only two frontend files are installed. ML, backend, datasets, and DB remain unchanged.
$files = @(
    @{ Path = 'src\components\InstructorDashboard.tsx'; Original = '581B0D94D2AA197ACC52EB64140104FD2F47526A7513C01AA9C0874AD10C9B3C'; Updated = '28EB4D3096FDF72E633454EC287CEC24A7497E21ABE68EF7B7F5C314BE6D8355' },
    @{ Path = 'src\global.css'; Original = '8B2C201F2669AD5CC9E3433B510D37D2BCF0D22D467B0372E4A36FB67385C5B1'; Updated = 'D9B90C2DB88B6AFD6E09E5B34ACA086FB5F5E00D55B69E5F146115A368A75841' }
)

# Check ALL source and destination hashes before writing anything.
$toInstall = @()
foreach ($file in $files) {
    $source = Join-Path $patchRoot $file.Path
    $destination = Join-Path $root $file.Path

    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Patch file is missing: $($file.Path)"
    }
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
        throw "STOPPED SAFELY: Your project is missing $($file.Path). No files changed."
    }

    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    if ($sourceHash -ne $file.Updated) {
        throw "Patch integrity check failed for $($file.Path). No files changed."
    }
    $currentHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if ($currentHash -eq $file.Updated) {
        Write-Host "Already updated: $($file.Path)" -ForegroundColor Green
        continue
    }
    if ($currentHash -ne $file.Original) {
        throw "STOPPED SAFELY: $($file.Path) differs from the reviewed version. No files changed. Send the latest file for a safe merge; do not force-overwrite."
    }
    $toInstall += $file
}

if ($toInstall.Count -eq 0) {
    Write-Host 'Premium instructor UI is already installed. No changes needed.' -ForegroundColor Green
    exit 0
}

# Full backups before any modifications.
$backupRoot = Join-Path $root ('_premium_instructor_backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
foreach ($file in $toInstall) {
    $backup = Join-Path $backupRoot $file.Path
    New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $root $file.Path) -Destination $backup -ErrorAction Stop
}

try {
    foreach ($file in $toInstall) {
        $destination = Join-Path $root $file.Path
        Copy-Item -LiteralPath (Join-Path $patchRoot $file.Path) -Destination $destination -Force -ErrorAction Stop
        if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $file.Updated) {
            throw "Hash verification failed after installing $($file.Path)"
        }
        Write-Host "Updated: $($file.Path)" -ForegroundColor Green
    }
} catch {
    Write-Warning 'Installation failed. Restoring backups...'
    foreach ($file in $toInstall) {
        Copy-Item -LiteralPath (Join-Path $backupRoot $file.Path) -Destination (Join-Path $root $file.Path) -Force
    }
    throw
}

Write-Host ''
Write-Host 'Premium instructor interface installed.' -ForegroundColor Green
Write-Host "Backups: $backupRoot"
Write-Host 'No CodeBERT training, backend, database or dataset files were modified.'
Write-Host 'Refresh localhost and check both light/dark and desktop/mobile views.'
