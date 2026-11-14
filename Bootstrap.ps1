param([string]$BaseArchive, [switch]$PrepareOnly)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
if($env:PROCESSOR_ARCHITECTURE -ne 'AMD64'){throw 'Windows x64 is required.'}
$baseUrl='https://github.com/ZGHJP/Win-CodexBar/releases/download/personal-v0.70.0-jp.5/CodexBar-0.70.0-jp.5-windows-x64.zip'
$baseHash='de7a26d89a001194a4b14d9702df615ec132eb49e2142b35fa7933ce497f7623'
$baseSource='da129a9214961540aa41a0a40fb1dea35fdba935'
$helperSource='dbfbd8d1a730769529dfb8e31f74cefb366a6043'
$work=Join-Path ([IO.Path]::GetTempPath()) ('CodexBar-jp6-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
if(-not $BaseArchive){
    $BaseArchive=Join-Path $work 'verified-native-base.zip'
    [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
    Write-Host 'Downloading the checksum-pinned compiled application...'
    Invoke-WebRequest -UseBasicParsing -Uri $baseUrl -OutFile $BaseArchive -TimeoutSec 120
}
if((Get-FileHash -LiteralPath $BaseArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $baseHash){throw 'Compiled base checksum mismatch. Nothing installed.'}
$package=Join-Path $work 'package'
Expand-Archive -LiteralPath $BaseArchive -DestinationPath $package
$manifestPath=Join-Path $package 'build-manifest.json'
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if($manifest.repository -ne 'ZGHJP/Win-CodexBar' -or $manifest.sourceCommit -ne $baseSource -or $manifest.personalVersion -ne '0.70.0-jp.5'){throw 'Unexpected compiled base source. Nothing installed.'}
$payload=Join-Path $PSScriptRoot 'payload'
foreach($line in Get-Content -LiteralPath (Join-Path $PSScriptRoot 'PAYLOAD-SHA256SUMS.txt')){
    if($line -notmatch '^([0-9a-f]{64})  (.+)$'){throw 'Invalid repair payload checksum list.'}
    $expected=$Matches[1]; $relative=$Matches[2]
    if($relative -notin @('compat.py','Install.ps1','RELEASE-NOTES.md')){throw 'Unexpected repair payload path.'}
    if((Get-FileHash -LiteralPath (Join-Path $payload $relative)).Hash.ToLowerInvariant() -ne $expected){throw 'Repair payload checksum mismatch.'}
}
Copy-Item -LiteralPath (Join-Path $payload 'compat.py') -Destination (Join-Path $package 'usage-compat\compat.py') -Force
Copy-Item -LiteralPath (Join-Path $payload 'Install.ps1') -Destination (Join-Path $package 'Install.ps1') -Force
Copy-Item -LiteralPath (Join-Path $payload 'RELEASE-NOTES.md') -Destination (Join-Path $package 'RELEASE-NOTES.md') -Force
$manifest | Add-Member -Force NoteProperty binarySourceCommit $baseSource
$manifest | Add-Member -Force NoteProperty binaryBuildNumber $manifest.buildNumber
$manifest | Add-Member -Force NoteProperty sourceCommit $helperSource
$manifest | Add-Member -Force NoteProperty personalVersion '0.70.0-jp.6'
$manifest | Add-Member -Force NoteProperty packageBuildNumber 'personal-0.70.0-jp.6-github-setup'
$manifest | Add-Member -Force NoteProperty packagingKind 'Compatibility repair over checksum-pinned jp.5 native binaries; native/frontend source unchanged'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$checksums=Get-ChildItem -LiteralPath $package -Recurse -File | Where-Object Name -NE 'SHA256SUMS.txt' | Sort-Object FullName | ForEach-Object {
    '{0}  {1}' -f (Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant(),$_.FullName.Substring($package.Length+1).Replace('\','/')
}
$checksums | Set-Content -LiteralPath (Join-Path $package 'SHA256SUMS.txt') -Encoding UTF8
if($PrepareOnly){Write-Output $package;return}
& (Join-Path $package 'Install.ps1') -PackageDirectory $package
Write-Host 'jp.6 credential repair installed. Original Codex credentials were retained.'
