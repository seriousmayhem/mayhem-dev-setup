. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

$exe = Join-Path $env:MAYHEM_BIN 'rg.exe'
if (-not (Test-Path $exe)) { exit 1 }
$have = (& $exe --version | Select-Object -First 1).Split(' ')[1]
$have
if ($have -ne (Get-Pin ripgrep)) { exit 1 }
exit 0
