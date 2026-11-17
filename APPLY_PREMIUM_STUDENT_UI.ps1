param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'

$sourceRel = 'src\components\StudentDashboard.tsx'
$styleRel = 'src\components\StudentDashboardPremium.css'
$targetSource = Join-Path $ProjectRoot $sourceRel
$targetStyle = Join-Path $ProjectRoot $styleRel
$patchSource = Join-Path $PSScriptRoot $sourceRel
$patchStyle = Join-Path $PSScriptRoot $styleRel

# Reviewed project snapshot (original source and the prior mobile-responsive update).
$allowedOriginalHashes = @(
  '6f126684458ec879d3526bda7d531d0f37bb5f33a99886bd906b178966ccf61b',
  '272029ce87a468605f6b81002f1777359d4525e76d70a6b3d305ffeaba2349f8'
)

foreach ($path in @($targetSource, $patchSource, $patchStyle)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Missing required file: $path. The patch was not installed."
  }
}
$sourceHash = (Get-FileHash -LiteralPath $targetSource -Algorithm SHA256).Hash.ToLowerInvariant()
$patchHash = (Get-FileHash -LiteralPath $patchSource -Algorithm SHA256).Hash.ToLowerInvariant()
$styleHash = (Get-FileHash -LiteralPath $patchStyle -Algorithm SHA256).Hash.ToLowerInvariant()

if ($sourceHash -notin $allowedOriginalHashes -and $sourceHash -ne $patchHash) {
  throw "STOPPED SAFELY: Your StudentDashboard.tsx differs from the reviewed versions. No files were changed. Share your latest StudentDashboard.tsx to prepare a compatible patch."
}
if ((Test-Path -LiteralPath $targetStyle -PathType Leaf) -and
    (Get-FileHash -LiteralPath $targetStyle -Algorithm SHA256).Hash.ToLowerInvariant() -ne $styleHash) {
  throw "STOPPED SAFELY: Your StudentDashboardPremium.css contains other changes. No files were changed."
}
if ($sourceHash -eq $patchHash -and (Test-Path -LiteralPath $targetStyle -PathType Leaf)) {
  Write-Host 'Already installed: the student UI files match this patch.' -ForegroundColor Green
  exit 0
}

$backup = Join-Path $ProjectRoot ('.codeauth-ui-backups\student-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -LiteralPath $targetSource -Destination (Join-Path $backup 'StudentDashboard.tsx') -Force
if (Test-Path -LiteralPath $targetStyle -PathType Leaf) {
  Copy-Item -LiteralPath $targetStyle -Destination (Join-Path $backup 'StudentDashboardPremium.css') -Force
}

try {
  Copy-Item -LiteralPath $patchStyle -Destination $targetStyle -Force
  Copy-Item -LiteralPath $patchSource -Destination $targetSource -Force
} catch {
  Copy-Item -LiteralPath (Join-Path $backup 'StudentDashboard.tsx') -Destination $targetSource -Force
  if (Test-Path -LiteralPath (Join-Path $backup 'StudentDashboardPremium.css') -PathType Leaf) {
    Copy-Item -LiteralPath (Join-Path $backup 'StudentDashboardPremium.css') -Destination $targetStyle -Force
  } else {
    Remove-Item -LiteralPath $targetStyle -ErrorAction SilentlyContinue
  }
  throw "The update was rolled back after a copy error: $_"
}

Write-Host 'SUCCESS: Premium student portal UI installed.' -ForegroundColor Green
Write-Host "Backup saved to: $backup"
Write-Host 'No backend, database, model, or Java training files were modified.'
Write-Host 'Refresh the local site, then test the student upload form on desktop and phone.'
