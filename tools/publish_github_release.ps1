[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$ArchivePath,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ChecksumPath,
    [string]$SymbolsPath = "",
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Repository = "",
    [ValidateSet("Stable", "Nightly")][string]$Channel = "Stable",
    [string]$ExpectedBranch = "main",
    [string]$ExpectedCommit = "",
    [string]$NotesFile = "",
    [switch]$Prerelease,
    [switch]$Publish,
    [switch]$UseExistingTag,
    [switch]$AllowDetachedHead,
    [switch]$ReplaceExistingAssets
)

# ZaeREo redistributes the GPL Quake II Rerelease DLL and the GPL Zaero source
# and assets under the GPL. Publishing a release is a deliberate, human-approved
# step: this script performs no GitHub mutation unless -Publish is passed, and it
# refuses to publish from a dirty tree or a commit that does not match the tag.
# Distribution rights are settled by the GPL; readiness/label is the caller's call.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-ExistingFile {
    param([string]$Path, [string]$Description)
    if ([string]::IsNullOrWhiteSpace($Path)) { throw "$Description path is empty." }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description not found: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

$workspacePath = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$archive = Resolve-ExistingFile $ArchivePath "Release archive"
$manifest = Resolve-ExistingFile $ManifestPath "External manifest"
$checksum = Resolve-ExistingFile $ChecksumPath "Checksum file"
$symbols = ""
if (-not [string]::IsNullOrWhiteSpace($SymbolsPath)) {
    $symbols = Resolve-ExistingFile $SymbolsPath "Symbols archive"
}

if ($Tag -notmatch '^v[0-9]') {
    throw "Release tag must look like a version tag (e.g. v0.1.0 or v0.1.0-nightly.*): $Tag"
}
if ($Channel -eq "Stable" -and $Tag -notmatch '^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$') {
    throw "Stable channel requires an exact vMAJOR.MINOR.PATCH tag: $Tag"
}
$isPrerelease = [bool]$Prerelease -or ($Channel -eq "Nightly")

# --- Verify the archive checksum matches the checksum file --------------------
$archiveName = Split-Path -Leaf $archive
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
$checksumLine = "$archiveHash  $archiveName"
if (@(Get-Content -LiteralPath $checksum) -notcontains $checksumLine) {
    throw "Checksum file does not bind the archive name and SHA-256 ($archiveHash  $archiveName)."
}

# --- Source-state safety (skippable only for detached/CI tag checkouts) -------
Push-Location $workspacePath
try {
    $commit = (& git rev-parse HEAD 2>$null).Trim()
    if ($ExpectedCommit -and $commit -and ($commit -ne $ExpectedCommit)) {
        throw "HEAD $commit does not match expected commit $ExpectedCommit."
    }
    if (-not $AllowDetachedHead) {
        $branch = (& git rev-parse --abbrev-ref HEAD 2>$null).Trim()
        if ($branch -ne $ExpectedBranch) {
            throw "Refusing to publish from branch '$branch'; expected '$ExpectedBranch' (or pass -AllowDetachedHead for a tag checkout)."
        }
    }
    $dirty = @(git status --porcelain --untracked-files=all)
    if ($dirty.Count -ne 0) {
        throw "Working tree is not clean; refusing to publish. Commit or stash first."
    }

    # --- Release notes --------------------------------------------------------
    if ($NotesFile -and (Test-Path -LiteralPath $NotesFile)) {
        $notesPath = (Resolve-Path -LiteralPath $NotesFile).Path
    }
    else {
        $notesPath = Join-Path ([IO.Path]::GetDirectoryName($archive)) "release-notes-$Tag.txt"
        $notes = @(
            "ZaeREo $Tag",
            "",
            "Unofficial GPL port of the 1998 Zaero mission pack to Quake II Rerelease.",
            "",
            "Version: $Version",
            "Commit: $commit",
            "Archive: $archiveName",
            "SHA-256: $archiveHash",
            "",
            "ZaeREo is free software under the GNU GPL v2. Zaero's original team",
            "(Team Evolve) released the Zaero source and assets under the GPL; the",
            "Quake II Rerelease game DLL is GPL-2.0. See LICENSE and THIRD_PARTY_NOTICES.md.",
            "Quake, Quake II, and Zaero marks belong to their respective owners; this",
            "project is unofficial and not endorsed by id Software, Bethesda, Nightdive,",
            "or Zaero's original team."
        ) -join [Environment]::NewLine
        Set-Content -LiteralPath $notesPath -Value $notes -Encoding ASCII
    }

    $assets = @($archive, $checksum, $manifest)
    if ($symbols) { $assets += $symbols }

    if (-not $Publish) {
        Write-Host "DRY RUN (no -Publish): would create GitHub release '$Tag'"
        Write-Host "  repository:  $(if ($Repository) { $Repository } else { '<current>' })"
        Write-Host "  prerelease:  $isPrerelease"
        Write-Host "  commit:      $commit"
        Write-Host "  notes:       $notesPath"
        Write-Host "  assets:"
        $assets | ForEach-Object { Write-Host "    $_" }
        return
    }

    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) { throw "GitHub CLI (gh) was not found in PATH. Install it and 'gh auth login', or run this from Actions with GH_TOKEN." }
    $repoArgs = @()
    if ($Repository) { $repoArgs += @("--repo", $Repository) }

    & $gh.Source @repoArgs release view $Tag *> $null
    $exists = ($LASTEXITCODE -eq 0)

    $prereleaseFlag = if ($isPrerelease) { "--prerelease" } else { "--latest" }

    if ($exists) {
        Write-Host "Release $Tag exists; editing notes and uploading assets."
        & $gh.Source @repoArgs release edit $Tag --title "ZaeREo $Tag" --notes-file $notesPath
        if ($LASTEXITCODE -ne 0) { throw "gh release edit failed." }
        $clobber = if ($ReplaceExistingAssets) { "--clobber" } else { $null }
        & $gh.Source @repoArgs release upload $Tag @assets $clobber
        if ($LASTEXITCODE -ne 0) { throw "gh release upload failed." }
    }
    else {
        Write-Host "Creating release $Tag."
        & $gh.Source @repoArgs release create $Tag @assets --title "ZaeREo $Tag" --notes-file $notesPath --target $commit $prereleaseFlag
        if ($LASTEXITCODE -ne 0) { throw "gh release create failed." }
    }

    Write-Host "Published $Tag ($(if ($isPrerelease) { 'prerelease' } else { 'latest' }))."
    if ($env:GITHUB_OUTPUT) {
        Add-Content -Path $env:GITHUB_OUTPUT -Value "published_tag=$Tag"
        Add-Content -Path $env:GITHUB_OUTPUT -Value "archive_sha256=$archiveHash"
    }
}
finally {
    Pop-Location
}
