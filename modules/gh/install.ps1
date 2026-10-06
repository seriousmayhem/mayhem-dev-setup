. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

$v = Get-Pin gh
$base = "https://github.com/cli/cli/releases/download/v$v"
$tmp = New-TempDir
try {
    Get-Verified "$base/gh_${v}_windows_amd64.zip" "$base/gh_${v}_checksums.txt" "$tmp\gh.zip"
    Expand-Archive -Path "$tmp\gh.zip" -DestinationPath "$tmp\x"
    Install-Bin "$tmp\x" 'gh.exe'
} finally {
    Remove-Item -Recurse -Force $tmp
}
