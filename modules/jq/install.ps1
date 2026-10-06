. (Join-Path $(if ($env:MAYHEM_LIB) { $env:MAYHEM_LIB } else { Join-Path $PSScriptRoot '..\_lib' }) 'lib.ps1')

$base = "https://github.com/jqlang/jq/releases/download/jq-$(Get-Pin jq)"
$tmp = New-TempDir
try {
    Get-Verified "$base/jq-windows-amd64.exe" "$base/sha256sum.txt" "$tmp\jq-windows-amd64.exe"
    Rename-Item "$tmp\jq-windows-amd64.exe" 'jq.exe'
    Install-Bin $tmp 'jq.exe'
} finally {
    Remove-Item -Recurse -Force $tmp
}
