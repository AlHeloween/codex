<#
sccache_setup.ps1
Installs and configures sccache (Rust "ccache-like" compiler cache) on Windows.

Usage examples:
  powershell -ExecutionPolicy Bypass -File .\sccache_setup.ps1
  powershell -ExecutionPolicy Bypass -File .\sccache_setup.ps1 -ProjectPath "C:\src\mycrate" -CacheSize "20G"
  powershell -ExecutionPolicy Bypass -File .\sccache_setup.ps1 -NoProjectConfig

What it does:
  1) Installs sccache (prefers winget/choco/scoop, else GitHub release download)
  2) Sets user env var RUSTC_WRAPPER=sccache
  3) Optionally writes .cargo/config.toml to set rustc-wrapper for a project
  4) Starts sccache server and prints stats
#>

[CmdletBinding()]
param(
  [string]$ProjectPath = (Get-Location).Path,
  [string]$InstallDir  = (Join-Path $env:LOCALAPPDATA "sccache\bin"),
  [string]$CacheDir    = (Join-Path $env:LOCALAPPDATA "sccache\cache"),
  [string]$CacheSize   = "10G",
  [switch]$NoProjectConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info([string]$Msg) { Write-Host "[INFO] $Msg" }
function Write-Warn([string]$Msg) { Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Write-Err ([string]$Msg) { Write-Host "[ERR ] $Msg" -ForegroundColor Red }

function Test-Command([string]$Name) {
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-Dir([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }
}

function Add-UserPath([string]$Dir) {
  $current = [Environment]::GetEnvironmentVariable("Path", "User")
  if ($null -eq $current) { $current = "" }

  $parts = $current.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries)
  $already = $false
  foreach ($p in $parts) {
    if ($p.TrimEnd("\") -ieq $Dir.TrimEnd("\")) { $already = $true; break }
  }

  if (-not $already) {
    $newPath = ($parts + $Dir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Info "Added to user PATH: $Dir"
  } else {
    Write-Info "Already on user PATH: $Dir"
  }
}

function Set-UserEnv([string]$Name, [string]$Value) {
  [Environment]::SetEnvironmentVariable($Name, $Value, "User")
  Write-Info "Set user env: $Name=$Value"
}

function Install-Sccache-Via-PackageManager {
  if (Test-Command "winget") {
    Write-Info "Installing sccache via winget..."
    & winget install --id Mozilla.sccache -e --source winget
    return $true
  }
  if (Test-Command "choco") {
    Write-Info "Installing sccache via chocolatey..."
    & choco install sccache -y
    return $true
  }
  if (Test-Command "scoop") {
    Write-Info "Installing sccache via scoop..."
    & scoop install sccache
    return $true
  }
  return $false
}

function Install-Sccache-From-GitHub([string]$TargetDir) {
  Ensure-Dir $TargetDir

  $api = "https://api.github.com/repos/mozilla/sccache/releases/latest"
  Write-Info "Querying GitHub releases API: $api"
  $release = Invoke-RestMethod -Uri $api -Headers @{ "User-Agent" = "PowerShell" }

  # Prefer Windows MSVC x86_64 zip
  $asset = $null
  foreach ($a in $release.assets) {
    $name = [string]$a.name
    if ($name -match "x86_64-pc-windows-msvc" -and $name -match "\.zip$") { $asset = $a; break }
  }

  if ($null -eq $asset) {
    throw "Could not find a suitable Windows x86_64 MSVC zip asset in latest release."
  }

  $zipUrl  = [string]$asset.browser_download_url
  $zipPath = Join-Path $env:TEMP $asset.name
  $tmpDir  = Join-Path $env:TEMP ("sccache_extract_" + [Guid]::NewGuid().ToString("N"))

  Write-Info "Downloading: $zipUrl"
  Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath

  Ensure-Dir $tmpDir
  Write-Info "Extracting to: $tmpDir"
  Expand-Archive -LiteralPath $zipPath -DestinationPath $tmpDir -Force

  # Find sccache.exe
  $exe = Get-ChildItem -Path $tmpDir -Recurse -Filter "sccache.exe" | Select-Object -First 1
  if ($null -eq $exe) {
    throw "sccache.exe not found after extraction."
  }

  $destExe = Join-Path $TargetDir "sccache.exe"
  Copy-Item -LiteralPath $exe.FullName -Destination $destExe -Force
  Write-Info "Installed: $destExe"

  # Cleanup
  Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
}

function Ensure-Sccache([string]$TargetDir) {
  if (Test-Command "sccache") {
    Write-Info "sccache already available in PATH."
    return
  }

  $installed = $false
  try {
    $installed = Install-Sccache-Via-PackageManager
  } catch {
    Write-Warn "Package-manager install attempt failed: $($_.Exception.Message)"
    $installed = $false
  }

  if (-not $installed) {
    Write-Info "No package manager available (or install failed); installing from GitHub release..."
    Install-Sccache-From-GitHub -TargetDir $TargetDir
    Add-UserPath -Dir $TargetDir
  } else {
    # refresh current session PATH from user PATH if needed
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($null -ne $userPath) { $env:Path = $env:Path + ";" + $userPath }
  }

  if (-not (Test-Command "sccache")) {
    throw "sccache still not found after installation. Restart your shell and re-run, or verify PATH."
  }
}

function Write-ProjectCargoConfig([string]$ProjPath) {
  $cargoDir = Join-Path $ProjPath ".cargo"
  Ensure-Dir $cargoDir

  $cfgPath = Join-Path $cargoDir "config.toml"
  $content = @"
[build]
rustc-wrapper = "sccache"
"@

  # If file exists, we do a conservative merge: add/replace build.rustc-wrapper only.
  if (Test-Path -LiteralPath $cfgPath) {
    $existing = Get-Content -LiteralPath $cfgPath -Raw

    if ($existing -match '^\s*\[build\]\s*$' -and $existing -match '^\s*rustc-wrapper\s*=\s*".*"\s*$') {
      $updated = ($existing -replace '(^\s*rustc-wrapper\s*=\s*)".*"\s*$', '${1}"sccache"', "Multiline")
      Set-Content -LiteralPath $cfgPath -Value $updated -Encoding UTF8
      Write-Info "Updated existing: $cfgPath (set build.rustc-wrapper)"
      return
    }

    # If no [build] section, append a minimal one.
    if (-not ($existing -match '^\s*\[build\]\s*$')) {
      $existing = $existing.TrimEnd() + "`r`n`r`n" + $content
      Set-Content -LiteralPath $cfgPath -Value $existing -Encoding UTF8
      Write-Info "Appended [build] section to: $cfgPath"
      return
    }

    # Has [build] but not rustc-wrapper: inject after [build] line
    $lines = Get-Content -LiteralPath $cfgPath
    $out = New-Object System.Collections.Generic.List[string]
    for ($i = 0; $i -lt $lines.Count; $i++) {
      $out.Add($lines[$i])
      if ($lines[$i].Trim() -eq "[build]") {
        $out.Add('rustc-wrapper = "sccache"')
      }
    }
    Set-Content -LiteralPath $cfgPath -Value ($out -join "`r`n") -Encoding UTF8
    Write-Info "Injected build.rustc-wrapper into: $cfgPath"
    return
  }

  Set-Content -LiteralPath $cfgPath -Value $content -Encoding UTF8
  Write-Info "Created: $cfgPath"
}

# --- Main ---
Write-Info "Ensuring sccache is installed..."
Ensure-Sccache -TargetDir $InstallDir

Write-Info "Configuring environment..."
Ensure-Dir $CacheDir
Set-UserEnv -Name "RUSTC_WRAPPER" -Value "sccache"
Set-UserEnv -Name "SCCACHE_DIR" -Value $CacheDir
Set-UserEnv -Name "SCCACHE_CACHE_SIZE" -Value $CacheSize

# Apply to current session too
$env:RUSTC_WRAPPER = "sccache"
$env:SCCACHE_DIR = $CacheDir
$env:SCCACHE_CACHE_SIZE = $CacheSize

if (-not $NoProjectConfig) {
  if (-not (Test-Path -LiteralPath $ProjectPath)) {
    throw "ProjectPath does not exist: $ProjectPath"
  }
  Write-Info "Writing project Cargo config in: $ProjectPath"
  Write-ProjectCargoConfig -ProjPath $ProjectPath
} else {
  Write-Info "Skipping project .cargo/config.toml as requested (-NoProjectConfig)."
}

Write-Info "Starting sccache server (if not running)..."
& sccache --start-server | Out-Null

Write-Info "sccache version:"
& sccache --version

Write-Info "sccache stats (initial):"
& sccache --show-stats

Write-Host ""
Write-Info "Done. Build as usual:"
Write-Host "  cargo build"
Write-Host "  cargo test"
Write-Host ""
Write-Info "After a few builds, check cache hit-rate:"
Write-Host "  sccache --show-stats"
