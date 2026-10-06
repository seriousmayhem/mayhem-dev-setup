. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { exit 1 }
$have = (git --version).Split(' ')[2]
$have
if ((ConvertTo-Version $have) -lt (ConvertTo-Version (Get-Pin git))) { exit 1 }
if ((git config --global core.longpaths) -ne 'true') { exit 1 }
if ((git config --global core.autocrlf) -ne 'false') { exit 1 }
if ($env:MAYHEM_USER_NAME -and -not (git config --global user.name)) { exit 1 }
if ($env:MAYHEM_USER_EMAIL -and -not (git config --global user.email)) { exit 1 }
exit 0
