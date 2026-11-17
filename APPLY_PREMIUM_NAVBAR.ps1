param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$patchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path

# This patch modifies ONLY the React navbar and global stylesheet.
# It never touches ml/, dataset/, backend/, database or training processes.
$files = @(
    @{ Path = "src\components\Navbar.tsx"; Original = "02854F6774EED82968B41641F485CEA8B84A688F3F378312DD0C6DE1F1081C37"; Updated = "B7730D15104314EBEF87A16AD1F98CC12DC0CA8BB80635CA54C822842EDD44D6" }
    @{ Path = "src\global.css"; Original = "03A94EE0F6B0FB76440CC9E6BEBB4DBF15FAE6317843E48DBA46CAE1331847DC"; Updated = "8B2C201F2669AD5CC9E3433B510D37D2BCF0D22D467B0372E4A36FB67385C5B1" }
 )
$toInstall = @()
foreach ($file in $files) {
    $destination = Join-Path $root $file.Path
    $source = Join-Path $patchRoot $file.Path
    if (!(Test-Path -LiteralPath $source -PathType Leaf)) { throw "Patch missing: $($file.Path)" }
    if (!(Test-Path -LiteralPath $destination -PathType Leaf)) { throw "STOPPED SAFELY: Project missing: $($file.Path)" }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $file.Updated) {
        throw "Patch integrity error: $($file.Path) was changed after packaging."
    }
    $currentHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if ($currentHash -eq $file.Updated) {
        Write-Host "Already updated: $($file.Path)" -ForegroundColor Green
        continue
    }
    if ($currentHash -ne $file.Original) {
        throw "STOPPED SAFELY: $($file.Path) has differences from the previous Mobile UI version. No files were changed. Send the current Navbar.tsx and global.css to merge safely."
    }
    $toInstall += $file
}
if ($toInstall.Count -eq 0) {
    Write-Host "Premium navigation patch already installed. No changes needed." -ForegroundColor Green
    exit 0
}
$backupRoot = Join-Path $root ("_navbar_backup_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
foreach ($file in $toInstall) {
    $backupPath = Join-Path $backupRoot $file.Path
    New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $root $file.Path) -Destination $backupPath -ErrorAction Stop
}
try {
    foreach ($file in $toInstall) {
        Copy-Item -LiteralPath (Join-Path $patchRoot $file.Path) -Destination (Join-Path $root $file.Path) -Force -ErrorAction Stop
        Write-Host "Updated: $($file.Path)" -ForegroundColor Green
    }
} catch {
    foreach ($file in $toInstall) {
        Copy-Item -LiteralPath (Join-Path $backupRoot $file.Path) -Destination (Join-Path $root $file.Path) -Force
    }
    throw
}
Write-Host ""
Write-Host "Premium navigation installed. Original files backed up in $backupRoot" -ForegroundColor Green
Write-Host "Only frontend navbar/CSS files changed. Java training and CodeBERT remain untouched."
