param([switch]$FrontendOnly)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'version.json') -Raw | ConvertFrom-Json
$previousBuild = $env:BUILD_NUMBER
try {
    $env:BUILD_NUMBER = "personal-$($version.version)"
    Push-Location (Join-Path $repoRoot 'apps/desktop-tauri')
    try {
        & pnpm.cmd install --frozen-lockfile
        if ($LASTEXITCODE) { throw 'Frontend dependency verification failed.' }
        & pnpm.cmd run build
        if ($LASTEXITCODE) { throw 'Frontend production build failed.' }
        if (-not $FrontendOnly) {
            & pnpm.cmd run tauri:build
            if ($LASTEXITCODE) { throw 'Tauri desktop build failed.' }
        }
    } finally { Pop-Location }
    if (-not $FrontendOnly) {
        Push-Location $repoRoot
        try {
            & cargo build -p codexbar --bin codexbar --release
            if ($LASTEXITCODE) { throw 'CLI build failed.' }
        } finally { Pop-Location }
    }
} finally {
    $env:BUILD_NUMBER = $previousBuild
}
