param(
    [Parameter(Mandatory=$true)][string]$DesktopExecutable,
    [Parameter(Mandatory=$true)][string]$CliExecutable,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [Parameter(Mandatory=$true)][string]$SourceCommit,
    [string]$PythonExecutable = 'python',
    [string]$PricingArtifactPath,
    [string]$BuildNumber = $env:BUILD_NUMBER
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $PSScriptRoot 'version.json') -Raw | ConvertFrom-Json).version
if ($SourceCommit -notmatch '^[0-9a-f]{40}$' -or -not $BuildNumber) { throw 'Exact source commit and build number are required.' }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Use a new empty output directory for each package.' }
$package = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path "$package\app", "$package\usage-compat\python-libs" -Force | Out-Null
Copy-Item -LiteralPath $DesktopExecutable -Destination "$package\app\codexbar-desktop.exe"
Copy-Item -LiteralPath $CliExecutable -Destination "$package\app\codexbar-cli.exe"
Copy-Item -LiteralPath (Join-Path $repoRoot 'rust\icons\icon.ico') -Destination "$package\app\icon.ico"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'usage-compat\compat.py') -Destination "$package\usage-compat\compat.py"
New-Item -ItemType Directory -Path "$package\pricing" | Out-Null
if ($PricingArtifactPath) {
    $pricing = Get-Content -LiteralPath $PricingArtifactPath -Raw | ConvertFrom-Json
    if ($pricing.version -ne 1 -or -not $pricing.fetched_at_unix_ms -or -not $pricing.catalog.providers.openai.models) { throw 'Invalid public pricing artifact.' }
    $pricingSeed = @{ version=1; fetched_at_unix_ms=$pricing.fetched_at_unix_ms; catalog=$pricing.catalog }
} else {
    $catalog = Invoke-RestMethod -Uri 'https://models.dev/api.json' -TimeoutSec 30
    if ($catalog.providers) { $catalog = $catalog.providers }
    if (-not $catalog.openai.models -or -not $catalog.anthropic.models) { throw 'Invalid public pricing catalog.' }
    $pricingSeed = @{ version=1; fetched_at_unix_ms=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); catalog=@{providers=$catalog} }
}
$pricingSeed | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath "$package\pricing\models-dev-v1.json" -Encoding utf8
foreach ($file in @('LICENSE','NOTICE')) { Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination $package }
foreach ($file in @('Install.ps1','Install.cmd','R6-R7-REIMPLEMENTATION.md','RELEASE-NOTES.md')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination $package
}
$runtime = Get-Content (Join-Path $PSScriptRoot 'python-runtime.json') -Raw | ConvertFrom-Json
$runtimeZip = "$package\python-runtime.zip"
Invoke-WebRequest -Uri $runtime.url -OutFile $runtimeZip
if ((Get-FileHash -LiteralPath $runtimeZip).Hash.ToLowerInvariant() -ne $runtime.sha256) { throw 'Python runtime checksum mismatch.' }
Expand-Archive -LiteralPath $runtimeZip -DestinationPath "$package\usage-compat\python"
Remove-Item -LiteralPath $runtimeZip
# Embeddable Python uses an explicit import path. Include only this package.
[IO.File]::WriteAllText("$package\usage-compat\python\python312._pth", "python312.zip`n.`n..`n../python-libs`n")
& $PythonExecutable -m pip install --only-binary=:all: --no-compile --target "$package\usage-compat\python-libs" --requirement (Join-Path $PSScriptRoot 'usage-compat\requirements.txt')
if ($LASTEXITCODE) { throw 'Compatibility dependency packaging failed.' }
& "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /reference:System.Windows.Forms.dll "/out:$package\app\codexbar.exe" (Join-Path $PSScriptRoot 'usage-compat\Launcher.cs')
if ($LASTEXITCODE) { throw 'Launcher build failed.' }
& "$package\usage-compat\python\python.exe" -c 'import sqlite3, ctypes, winreg, zstandard; print("Bundled runtime ready")'
if ($LASTEXITCODE) { throw 'Bundled runtime smoke check failed.' }
& "$package\app\codexbar-cli.exe" --version
if ($LASTEXITCODE) { throw 'CLI smoke check failed.' }
@{
    repository='ZGHJP/Win-CodexBar'; sourceCommit=$SourceCommit; personalVersion=$version;
    buildNumber=$BuildNumber; python=$runtime.version; signing='Unsigned personal build';
    pricing='API equivalent estimate, not subscription or credits billing';
    pricingSeedFetchedAtMs=$pricingSeed.fetched_at_unix_ms
} | ConvertTo-Json | Set-Content -LiteralPath "$package\build-manifest.json" -Encoding utf8
Get-ChildItem -LiteralPath $package -Recurse -File | Sort-Object FullName | ForEach-Object {
    $relative = $_.FullName.Substring($package.Length + 1).Replace('\','/')
    '{0}  {1}' -f (Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant(), $relative
} | Set-Content -LiteralPath "$package\SHA256SUMS.txt" -Encoding utf8
Compress-Archive -Path "$package\*" -DestinationPath "$package.zip"
(Get-FileHash -LiteralPath "$package.zip").Hash.ToLowerInvariant() + '  ' + [IO.Path]::GetFileName("$package.zip") |
    Set-Content -LiteralPath "$package.zip.sha256" -Encoding utf8
Write-Output "Package: $package.zip"
