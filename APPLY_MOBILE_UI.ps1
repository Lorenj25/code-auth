param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference = "Stop"
$patchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path

# Only frontend files are part of this package; no model, Python or database files are touched.
$files = @(
    @{ Path = "src\App.tsx"; Original = "afcc34bcdef82c62aea44d455a5d44ea617380c16e2ada9399e69e135b7a6e13"; Updated = "8021974972b7302e1f19f55e0c54736c27096af2a7eabc4ec275a394ee2ff90d" }
    @{ Path = "src\global.css"; Original = "0929d5fae32ffd6725d2a97a45cf16fefa0a1ec70b47b2beed6d11ea1265076e"; Updated = "03a94ee0f6b0fb76440cc9e6bebb4dbf15fae6317843e48dba46cae1331847dc" }
    @{ Path = "src\components\Navbar.tsx"; Original = "70b9bb68c86a1386c88b24d1d82db5ce364687daf3f7b05da8fff585d3cdc89a"; Updated = "02854f6774eed82968b41641f485cea8b84a688f3f378312dd0c6de1f1081c37" }
    @{ Path = "src\components\HomeIntro.tsx"; Original = "c0aac87979e8f0fada539cf43537cb90dd024b0859b44d3e0719cbda541a4d5c"; Updated = "1b593baf329adad0514741f97d4c47728045e56639f333c0242bf0d976e95985" }
    @{ Path = "src\components\InstructorLogin.tsx"; Original = "3ae94f9725b4ebc438b1bcf2266656a95bf3519390b84fc4de4498254d110d24"; Updated = "407e6a8e1a3ff0d7443335d5881971876e0b4df35ad1ee9f450fc33db590e578" }
    @{ Path = "src\components\StudentDashboard.tsx"; Original = "6f126684458ec879d3526bda7d531d0f37bb5f33a99886bd906b178966ccf61b"; Updated = "272029ce87a468605f6b81002f1777359d4525e76d70a6b3d305ffeaba2349f8" }
    @{ Path = "src\components\InstructorDashboard.tsx"; Original = "13bb091bbe7073a2bba53105430f7e11d5660224aae2f17b5fee580c70266e90"; Updated = "581b0d94d2aa197acc52eb64140104fd2f47526a7513c01aa9c0874ad10c9b3c" }
    @{ Path = "src\components\CodeModal.tsx"; Original = "4936c82e3cf733a93c950787f029e0ffddb32e9bb5fc2febc80d8cdef40369d7"; Updated = "53cf961d65a3793e9a42f7200fe6e21987cad7ed02999f6885385b875cb3237b" }
)
$toInstall = @()
foreach ($file in $files) {
    $destination = Join-Path $root $file.Path
    $source = Join-Path $patchRoot $file.Path
    if (!(Test-Path -LiteralPath $destination -PathType Leaf)) { throw "STOPPED SAFELY: missing project file: $($file.Path)" }
    if (!(Test-Path -LiteralPath $source -PathType Leaf)) { throw "Patch is missing $($file.Path)" }
    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    if ($sourceHash -ne $file.Updated) { throw "Patch integrity check failed for $($file.Path)" }
    $current = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if ($current -eq $file.Updated) {
        Write-Host "Already updated: $($file.Path)"
        continue
    }
    if ($current -ne $file.Original) {
        throw "STOPPED SAFELY: $($file.Path) differs from the reviewed source ZIP. No files were changed. Use an updated project ZIP to merge changes without overwriting newer work."
    }
    $toInstall += $file
}
if ($toInstall.Count -eq 0) { Write-Host "Mobile UI patch is already installed. No changes needed."; exit 0 }
$backupRoot = Join-Path $root ("_mobile_ui_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
# Create every backup before replacing any project file.
foreach ($file in $toInstall) {
    $destination = Join-Path $root $file.Path
    $backup = Join-Path $backupRoot $file.Path
    New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
    Copy-Item -LiteralPath $destination -Destination $backup -ErrorAction Stop
}
try {
    foreach ($file in $toInstall) {
        Copy-Item -LiteralPath (Join-Path $patchRoot $file.Path) -Destination (Join-Path $root $file.Path) -Force -ErrorAction Stop
        Write-Host "Updated: $($file.Path)"
    }
} catch {
    Write-Warning "Installation failed, restoring original frontend files from backup..."
    foreach ($file in $toInstall) {
        Copy-Item -LiteralPath (Join-Path $backupRoot $file.Path) -Destination (Join-Path $root $file.Path) -Force
    }
    throw
}
Write-Host ""
Write-Host "Mobile UI update installed. Backup: $backupRoot"
Write-Host "Only frontend layout/styling files changed. No CodeBERT training, backend or dataset files were modified."
