# Dot-sourced by module scripts. Works under the CLI (which sets MAYHEM_*) and by hand.
# Windows PowerShell 5.1 compatible: it's the shell every Windows machine has.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # 5.1's progress bar makes downloads crawl
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (-not $env:MAYHEM_BIN) { $env:MAYHEM_BIN = Join-Path $HOME '.local\bin' }

# MAYHEM_VERSION when the CLI set it, else the name's line in the public versions.toml.
function Get-Pin($Name) {
    if ($env:MAYHEM_VERSION) { return $env:MAYHEM_VERSION }
    $file = Join-Path $PSScriptRoot '..\..\versions.toml'
    foreach ($line in Get-Content $file) {
        if ($line -match "^$Name\s*=\s*`"([^`"]+)`"") { return $Matches[1] }
    }
    throw "no pin for $Name in $file"
}

function ConvertTo-Version($Text) {
    [version](([regex]::Matches($Text, '\d+') | Select-Object -First 3 | ForEach-Object { $_.Value }) -join '.')
}

# Download Url to Out and check it against SumsUrl: either sha256sum format (a line per file)
# or certutil's (one bare hash between a header and a footer, as ripgrep's Windows assets ship).
function Get-Verified($Url, $SumsUrl, $Out) {
    $name = $Url.Split('/')[-1]
    $sumsFile = "$Out.sums"
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Out
    Invoke-WebRequest -UseBasicParsing -Uri $SumsUrl -OutFile $sumsFile
    $lines = Get-Content $sumsFile
    Remove-Item $sumsFile
    $want = foreach ($line in $lines) {
        $parts = $line.Trim() -split '\s+'
        if ($parts[1] -eq $name -or $parts[1] -eq "*$name") { $parts[0].ToLower() }
    }
    if (-not $want) {
        $bare = @($lines | ForEach-Object { $_ -replace '\s', '' } | Where-Object { $_ -match '^[0-9a-fA-F]{64}$' })
        if ($bare.Count -eq 1) { $want = $bare[0].ToLower() }
    }
    if (-not $want) { throw "$name is not listed in $SumsUrl" }
    $got = (Get-FileHash -Algorithm SHA256 $Out).Hash.ToLower()
    if ($want -ne $got) { throw "checksum mismatch for $name" }
}

# Copy the first file called Name under Dir into MAYHEM_BIN.
function Install-Bin($Dir, $Name) {
    $src = Get-ChildItem -Recurse -File -Path $Dir -Filter $Name | Select-Object -First 1
    if (-not $src) { throw "$Name not found in the download" }
    New-Item -ItemType Directory -Force -Path $env:MAYHEM_BIN | Out-Null
    Copy-Item -Force $src.FullName (Join-Path $env:MAYHEM_BIN $Name)
}

function New-TempDir {
    $dir = Join-Path ([IO.Path]::GetTempPath()) ([IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $dir | Out-Null
    $dir
}
