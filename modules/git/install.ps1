. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git -or (ConvertTo-Version (git --version)) -lt (ConvertTo-Version (Get-Pin git))) {
    winget install --id Git.Git --exact --silent --disable-interactivity --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "winget install Git.Git failed ($LASTEXITCODE)" }
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

git config --global core.longpaths true
git config --global core.autocrlf false
# Fill in identity only where it's missing; never overwrite what the person set.
if ($env:MAYHEM_USER_NAME -and -not (git config --global user.name)) { git config --global user.name $env:MAYHEM_USER_NAME }
if ($env:MAYHEM_USER_EMAIL -and -not (git config --global user.email)) { git config --global user.email $env:MAYHEM_USER_EMAIL }
