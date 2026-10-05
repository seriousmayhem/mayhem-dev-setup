# irm https://github.com/seriousmayhem/mayhem-dev-setup/releases/latest/download/bootstrap.ps1 | iex
# & ([scriptblock]::Create((irm .../bootstrap.ps1))) --profile human --yes
#
# Installs git and uv, checks out the latest signed release into ~/.mayhem/setup, installs the
# mayhem CLI from it and runs `mayhem setup ARGS`.
#   $env:MAYHEM_REF = '<tag|branch|sha>'  converge something other than the latest release tag
#   --allow-unsigned                       required when the ref isn't a tag signed by $AllowedSigners
#
# Runs under Windows PowerShell 5.1, so no PS7-only syntax. Never `exit`: under iex it closes
# the user's shell. Never redirect native stderr: 5.1 turns it into terminating errors.

function Invoke-MayhemBootstrap {
    param([string[]]$SetupArgs)

    $ErrorActionPreference = 'Stop'
    $RepoUrl = if ($env:MAYHEM_REPO_URL) { $env:MAYHEM_REPO_URL } else { 'https://github.com/seriousmayhem/mayhem-dev-setup.git' }
    # Must match allowed_signers at the repo root (the release workflow checks).
    $AllowedSigners = 'release@mayhem-dev-setup namespaces="git" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINyqq6OqUQSxwQ4M5zCAjwsa8ToAYXP9Dd2YG+eTcPar'

    function Say($Message) { Write-Host "==> $Message" }
    function Invoke-Native {
        & $args[0] $args[1..($args.Count - 1)]
        if ($LASTEXITCODE -ne 0) { throw "$($args -join ' ') failed ($LASTEXITCODE)" }
    }
    function Update-SessionPath {
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path', 'User')
    }
    function Install-WingetPackage($Id) {
        Say "Installing $Id"
        Invoke-Native winget install --id $Id --exact --silent --disable-interactivity `
            --accept-source-agreements --accept-package-agreements
        Update-SessionPath
    }
    function Test-Command($Name) { [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

    $allowUnsigned = $false
    $passThrough = @()
    foreach ($arg in $SetupArgs) {
        if ($arg -eq '--allow-unsigned') { $allowUnsigned = $true } else { $passThrough += $arg }
    }

    if (-not (Test-Command git)) { Install-WingetPackage Git.Git }
    if (-not (Test-Command uv)) { Install-WingetPackage astral-sh.uv }

    $mayhemHome = if ($env:MAYHEM_HOME) { $env:MAYHEM_HOME } else { Join-Path $HOME '.mayhem' }
    $dest = Join-Path $mayhemHome 'setup'
    $ref = $env:MAYHEM_REF
    if (-not $ref) {
        $line = git ls-remote --tags --refs --sort=-v:refname $RepoUrl 'v*' | Select-Object -First 1
        if (-not $line) { throw "no v* release tag on $RepoUrl (set `$env:MAYHEM_REF and pass --allow-unsigned)" }
        $ref = ($line -split 'refs/tags/')[1]
    }

    if (-not (Test-Path (Join-Path $dest '.git'))) {
        Say "Cloning $RepoUrl into $dest"
        New-Item -ItemType Directory -Force -Path $mayhemHome | Out-Null
        Invoke-Native git clone --quiet --no-checkout $RepoUrl $dest
    }
    # No --force on tags: a release tag that moved upstream must fail here, not get adopted.
    Invoke-Native git -C $dest fetch --quiet --tags origin '+refs/heads/*:refs/remotes/origin/*'

    $signers = [IO.Path]::GetTempFileName()
    try {
        [IO.File]::WriteAllText($signers, "$AllowedSigners`n")
        git -C $dest -c gpg.format=ssh -c "gpg.ssh.allowedSignersFile=$signers" verify-tag "refs/tags/$ref" | Out-Null
        $verified = $LASTEXITCODE -eq 0
    } finally {
        Remove-Item -Force $signers
    }
    if ($verified) {
        Say "Verified signed release $ref"
    } elseif ($allowUnsigned) {
        Say "WARNING: converging unsigned ref $ref"
    } else {
        throw "$ref is not a release tag signed by an allowed key (pass --allow-unsigned to override)"
    }

    $commit = $null
    foreach ($candidate in "refs/tags/$ref", "refs/remotes/origin/$ref", $ref) {
        $commit = git -C $dest rev-parse -q --verify "$candidate^{commit}"
        if ($LASTEXITCODE -eq 0) { break }
        $commit = $null
    }
    if (-not $commit) { throw "unknown ref $ref" }
    Invoke-Native git -C $dest -c advice.detachedHead=false checkout --quiet --force --detach $commit

    Say 'Installing the mayhem CLI'
    Invoke-Native uv tool install --quiet --force --editable $dest
    $bin = Join-Path (uv tool dir --bin) 'mayhem.exe'
    Invoke-Native $bin setup @passThrough
}

# Called last so a truncated download runs nothing.
Invoke-MayhemBootstrap $args
