. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

$userPath = (Get-Item 'HKCU:\Environment').GetValue('Path', '', 'DoNotExpandEnvironmentNames')
$entries = $userPath -split ';' | ForEach-Object { [Environment]::ExpandEnvironmentVariables($_).TrimEnd('\') }
if ($entries -notcontains $env:MAYHEM_BIN.TrimEnd('\')) { exit 1 }
$env:MAYHEM_BIN
