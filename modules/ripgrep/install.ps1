. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

$v = Get-Pin ripgrep
$url = "https://github.com/BurntSushi/ripgrep/releases/download/$v/ripgrep-$v-x86_64-pc-windows-msvc.zip"
$tmp = New-TempDir
try {
    Get-Verified $url "$url.sha256" "$tmp\rg.zip"
    Expand-Archive -Path "$tmp\rg.zip" -DestinationPath "$tmp\x"
    Install-Bin "$tmp\x" 'rg.exe'
} finally {
    Remove-Item -Recurse -Force $tmp
}
