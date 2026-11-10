param([string]$PackageDirectory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$packageRoot = (Resolve-Path -LiteralPath $PackageDirectory).Path.TrimEnd('\')
$manifest = Get-Content -LiteralPath (Join-Path $packageRoot 'build-manifest.json') -Raw | ConvertFrom-Json
if ($manifest.repository -ne 'ZGHJP/Win-CodexBar' -or $manifest.personalVersion -ne '0.70.0-jp.5') {
    throw 'Unexpected personal package identity.'
}
if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') { throw 'Windows x64 is required.' }
foreach ($line in Get-Content -LiteralPath (Join-Path $packageRoot 'SHA256SUMS.txt')) {
    if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { throw 'Invalid checksum entry.' }
    $expected = $Matches[1]
    $relative = $Matches[2]
    if ([IO.Path]::IsPathRooted($relative)) { throw 'Absolute package path rejected.' }
    $file = [IO.Path]::GetFullPath((Join-Path $packageRoot $relative))
    if (-not $file.StartsWith($packageRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Package path escapes its directory.' }
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Checksum mismatch: $relative" }
}
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\CodexBar'
$compatDir = Join-Path $env:LOCALAPPDATA 'CodexBar\usage-compat'
$python = Join-Path $packageRoot 'usage-compat\python\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'The bundled Python runtime is missing. Download and extract the complete package.' }
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^codexbar.*\.exe$' }
if ($running) { throw 'Quit CodexBar before installing. Your settings and usage data will be retained.' }
$companion = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -and
    $_.CommandLine.IndexOf((Join-Path $compatDir 'compat.py'), [StringComparison]::OrdinalIgnoreCase) -ge 0
}
if ($companion) { throw 'The CodexBar companion is still closing. Wait about 45 seconds, then run Install.cmd again.' }
$backup = Join-Path $env:LOCALAPPDATA ('CodexBar\install-backups\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup, $installDir, $compatDir -Force | Out-Null
if (Test-Path -LiteralPath (Join-Path $installDir 'codexbar-desktop.exe')) {
    Copy-Item -LiteralPath $installDir -Destination (Join-Path $backup 'app') -Recurse
}
if (Test-Path -LiteralPath (Join-Path $compatDir 'compat.py')) {
    Copy-Item -LiteralPath (Join-Path $compatDir 'compat.py') -Destination $backup
}
Get-ChildItem -LiteralPath (Join-Path $packageRoot 'app') -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $installDir $_.Name) -Force
}
foreach ($notice in @('LICENSE', 'NOTICE', 'build-manifest.json', 'SHA256SUMS.txt', 'R6-R7-REIMPLEMENTATION.md','RELEASE-NOTES.md')) {
    Copy-Item -LiteralPath (Join-Path $packageRoot $notice) -Destination (Join-Path $installDir $notice) -Force
}
Copy-Item -LiteralPath (Join-Path $packageRoot 'usage-compat\compat.py') -Destination (Join-Path $compatDir 'compat.py') -Force
Copy-Item -LiteralPath (Join-Path $packageRoot 'usage-compat\python-libs') -Destination $compatDir -Recurse -Force
Copy-Item -LiteralPath (Join-Path $packageRoot 'usage-compat\python') -Destination $compatDir -Recurse -Force
[IO.File]::WriteAllText((Join-Path $compatDir 'native-pr779.enabled'), 'native workspace snapshot refresh is available')
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'CodexBar.lnk'))
$shortcut.TargetPath = Join-Path $installDir 'codexbar.exe'
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = (Join-Path $installDir 'icon.ico') + ',0'
$shortcut.Description = 'ZGHJP personal Win-CodexBar ' + $manifest.personalVersion
$shortcut.Save()
& (Join-Path $installDir 'codexbar-cli.exe') --version
if ($LASTEXITCODE) { throw 'Installed CLI smoke check failed.' }
$installation = [ordered]@{
    installedAt = [DateTimeOffset]::Now.ToString('o')
    computer = $env:COMPUTERNAME
    user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    installDir = $installDir
    backup = $backup
    package = $manifest
    binaries = @(Get-ChildItem -LiteralPath $installDir -Filter '*.exe' | ForEach-Object {
        [pscustomobject]@{file=$_.Name;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant();version=$_.VersionInfo.FileVersion}
    })
}
$installation | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $compatDir 'native-build.json') -Encoding utf8
Start-Process -FilePath (Join-Path $installDir 'codexbar.exe') -WorkingDirectory $installDir -WindowStyle Hidden
$installation | ConvertTo-Json -Depth 8
