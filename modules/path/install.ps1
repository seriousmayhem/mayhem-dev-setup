. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

# Edit the registry value raw: [Environment]::SetEnvironmentVariable would expand and
# flatten any %VAR% entries already in the user's PATH.
$key = Get-Item 'HKCU:\Environment'
$userPath = $key.GetValue('Path', '', 'DoNotExpandEnvironmentNames')
$entries = $userPath -split ';' | ForEach-Object { [Environment]::ExpandEnvironmentVariables($_).TrimEnd('\') }
if ($entries -notcontains $env:MAYHEM_BIN.TrimEnd('\')) {
    $new = (@($userPath.TrimEnd(';'), $env:MAYHEM_BIN) | Where-Object { $_ }) -join ';'
    Set-ItemProperty -Path 'HKCU:\Environment' -Name Path -Value $new -Type ExpandString
    # Clearing an unset variable this way broadcasts WM_SETTINGCHANGE, so new shells see the PATH.
    [Environment]::SetEnvironmentVariable('MAYHEM_PATH_REFRESH', $null, 'User')
}
