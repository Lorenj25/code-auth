param(
  [Parameter(Mandatory=$true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'

if (!(Test-Path $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}

$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$files = @(
  'src/components/Navbar.tsx',
  'src/global.css'
)

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupRoot = Join-Path $ProjectRoot ("backup_premium_logout_modal_" + $timestamp)
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

foreach ($relative in $files) {
  $src = Join-Path $sourceRoot $relative
  $dst = Join-Path $ProjectRoot $relative

  if (!(Test-Path $src)) {
    throw "Patch file missing: $src"
  }
  if (!(Test-Path $dst)) {
    throw "Target file missing: $dst"
  }

  $backupPath = Join-Path $backupRoot $relative
  New-Item -ItemType Directory -Path (Split-Path $backupPath) -Force | Out-Null
  Copy-Item $dst $backupPath -Force

  Copy-Item $src $dst -Force
  Write-Host "Updated: $relative"
}

Write-Host ""
Write-Host "Premium logout modal installed successfully."
Write-Host "Backup created at: $backupRoot"
