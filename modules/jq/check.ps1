. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

$exe = Join-Path $env:MAYHEM_BIN 'jq.exe'
if (-not (Test-Path $exe)) { exit 1 }
$have = (& $exe --version) -replace '^jq-', ''
$have
if ($have -ne (Get-Pin jq)) { exit 1 }
exit 0
