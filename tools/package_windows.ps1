[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Medium")]
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateSet("Release")]
    [string]$Configuration = "Release",
    [ValidateSet("importer-kit", "local-full")]
    [string]$DistributionMode = "importer-kit",
    [string]$ZaeroLegacyRoot = "",
    [string]$ImportedContentRoot = "",
    [string]$AssetManifest = "",
    [string]$VcpkgInstalledRoot = "",
    [string]$DistRoot = "",
    [string]$ArtifactLabel = "",
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [switch]$AllowDirty,
    [switch]$IncludeSymbols
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "zaereo_paths.ps1")

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path, [string]$Base = "")
    $expanded = [Environment]::ExpandEnvironmentVariables($Path.Trim())
    if (-not [IO.Path]::IsPathRooted($expanded)) {
        if (-not $Base) { throw "A base path is required for '$Path'." }
        $expanded = Join-Path $Base $expanded
    }
    return [IO.Path]::GetFullPath($expanded)
}

function Assert-StrictChildPath {
    param([string]$Parent, [string]$Child, [string]$Description = "path")
    $parentPath = (Get-FullPath $Parent).TrimEnd("\", "/")
    $childPath = (Get-FullPath $Child).TrimEnd("\", "/")
    if (-not $childPath.StartsWith($parentPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Description must remain below '$parentPath': $childPath"
    }
    return $childPath
}

function Reset-OwnedDirectory {
    param([string]$OwnedRoot, [string]$Target)
    $safe = Assert-StrictChildPath $OwnedRoot $Target "generated directory"
    if (Test-Path -LiteralPath $safe) {
        $item = Get-Item -LiteralPath $safe -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to recursively remove a reparse point: $safe"
        }
        Remove-Item -LiteralPath $safe -Recurse -Force
    }
    New-Item -ItemType Directory -Path $safe -Force | Out-Null
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) { return @($launcher.Source, "-3") }
    throw "Python 3 was not found in PATH."
}

function Invoke-PythonTool {
    param([string[]]$PythonCommand, [string]$Script, [string[]]$Arguments)
    $command = $PythonCommand[0]
    $prefix = @($PythonCommand | Select-Object -Skip 1)
    & $command @prefix $Script @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python tool failed with exit code ${LASTEXITCODE}: $Script"
    }
}

function Get-LocalConfiguration {
    param([string]$WorkspacePath)
    return Get-ZaeREoLocalConfiguration $WorkspacePath
}

function Get-ConfigString {
    param([object]$Configuration, [string[]]$Names)
    return Get-ZaeREoConfigurationValue $Configuration $Names
}

function Resolve-PathByPrecedence {
    param(
        [string]$Explicit,
        [string]$EnvironmentName,
        [object]$Configuration,
        [string[]]$ConfigNames,
        [string]$WorkspacePath,
        [string]$Discovery,
        [string]$Description
    )
    $safeDiscovery = $null
    if ($Discovery) {
        $discoveryPath = $Discovery
        $safeDiscovery = {
            if (Test-Path -LiteralPath $discoveryPath) { $discoveryPath } else { "" }
        }.GetNewClosure()
    }
    $environmentNames = if ($EnvironmentName) { @($EnvironmentName) } else { @() }
    return Resolve-ZaeREoPath `
        -ExplicitValue $Explicit `
        -EnvironmentNames $environmentNames `
        -Configuration $Configuration `
        -ConfigurationNames $ConfigNames `
        -WorkspacePath $WorkspacePath `
        -Discovery $safeDiscovery `
        -Description $Description
}

function Get-SafeDestination {
    param([string]$Root, [string]$Relative)
    if (-not $Relative -or [IO.Path]::IsPathRooted($Relative) -or
        $Relative.Contains(":") -or $Relative -match '(^|[\\/])\.\.([\\/]|$)') {
        throw "Unsafe relative path: '$Relative'"
    }
    return (Assert-StrictChildPath $Root (Join-Path $Root $Relative) "copied file")
}

function Copy-TreeFiles {
    param([string]$Source, [string]$Destination, [string[]]$ExcludeRelative = @())
    $sourcePath = Get-FullPath $Source
    $destinationPath = Get-FullPath $Destination
    $excluded = @{}
    foreach ($relative in $ExcludeRelative) {
        $excluded[$relative.Replace("\", "/").ToLowerInvariant()] = $true
    }
    foreach ($directory in Get-ChildItem -LiteralPath $sourcePath -Directory -Recurse -Force) {
        if ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to traverse a reparse-point directory: $($directory.FullName)"
        }
    }
    foreach ($file in Get-ChildItem -LiteralPath $sourcePath -File -Recurse -Force) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to package a reparse point: $($file.FullName)"
        }
        $relative = [IO.Path]::GetRelativePath($sourcePath, $file.FullName)
        if ($excluded.ContainsKey($relative.Replace("\", "/").ToLowerInvariant())) { continue }
        $target = Get-SafeDestination $destinationPath $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target -Force
    }
}

function Assert-NoTreeCollisions {
    param([string]$FirstRoot, [string]$SecondRoot, [string]$Description)

    $first = Get-FullPath $FirstRoot
    $second = Get-FullPath $SecondRoot
    foreach ($file in Get-ChildItem -LiteralPath $second -File -Recurse -Force) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to inspect a reparse point: $($file.FullName)"
        }
        $relative = [IO.Path]::GetRelativePath($second, $file.FullName)
        $candidate = Get-SafeDestination $first $relative
        if (Test-Path -LiteralPath $candidate) {
            throw "$Description has an ownership collision at $relative"
        }
        $parentRelative = Split-Path -Parent $relative
        while ($parentRelative) {
            $parent = Get-SafeDestination $first $parentRelative
            if (Test-Path -LiteralPath $parent -PathType Leaf) {
                throw "$Description has a file/directory ownership collision at $parentRelative"
            }
            $parentRelative = Split-Path -Parent $parentRelative
        }
    }
}

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    [IO.File]::WriteAllText($Path, $Content.Replace("`r`n", "`n"), [Text.UTF8Encoding]::new($false))
}

function Get-GitOutput {
    param([string]$WorkspacePath, [string[]]$Arguments)
    $output = (& git -C $WorkspacePath @Arguments 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Git command failed: git $($Arguments -join ' ')" }
    return $output
}

function Set-GitHubOutput {
    param([string]$Name, [string]$Value)
    if ($env:GITHUB_OUTPUT) {
        Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "$Name=$Value" -Encoding utf8
    }
}

$workspacePath = Get-FullPath $WorkspaceRoot
if (-not (Test-Path -LiteralPath $workspacePath -PathType Container)) {
    throw "Workspace does not exist: $workspacePath"
}
$versionPath = Join-Path $workspacePath "VERSION"
if (-not (Test-Path -LiteralPath $versionPath -PathType Leaf)) {
    throw "VERSION is missing: $versionPath"
}
$version = (Get-Content -LiteralPath $versionPath -Raw).Trim()
if ($version -notmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$') {
    throw "VERSION is not a supported semantic version: '$version'"
}
$commit = Get-GitOutput $workspacePath @("rev-parse", "HEAD")
$sourceDateEpochText = Get-GitOutput $workspacePath @("show", "-s", "--format=%ct", $commit)
[long]$sourceDateEpoch = 0
if (-not [long]::TryParse($sourceDateEpochText, [ref]$sourceDateEpoch) -or $sourceDateEpoch -lt 0) {
    throw "Git commit has an invalid source date epoch: '$sourceDateEpochText'"
}
$status = Get-GitOutput $workspacePath @("status", "--porcelain=v1", "--untracked-files=all")
$isDirty = [bool]$status
if ($isDirty -and -not $AllowDirty) {
    throw "Packaging requires a clean worktree. Commit/stash changes or pass -AllowDirty for a local, non-publishable verification artifact."
}

if (-not $ArtifactLabel) { $ArtifactLabel = "v$version" }
if ($ArtifactLabel -notmatch '^[0-9A-Za-z][0-9A-Za-z._-]*$') {
    throw "ArtifactLabel contains unsafe filename characters: '$ArtifactLabel'"
}
$configurationData = Get-LocalConfiguration $workspacePath
$distPath = if ($DistRoot.Trim()) { Get-FullPath $DistRoot $workspacePath } else { Join-Path $workspacePath "dist" }
$defaultDist = Join-Path $workspacePath "dist"
if ((Get-FullPath $distPath) -ne (Get-FullPath $defaultDist)) {
    Write-Host "Using explicit release output root: $distPath"
}
if (Test-Path -LiteralPath $distPath) {
    $distItem = Get-Item -LiteralPath $distPath -Force
    if (-not $distItem.PSIsContainer -or $distItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Release output root must be a real directory, not a file or reparse point: $distPath"
    }
}

$python = Get-PythonCommand
$buildTool = Join-Path $workspacePath "tools\build_game.ps1"
$verifyBinaryTool = Join-Path $workspacePath "tools\verify_binary.ps1"
$checkProjectTool = Join-Path $workspacePath "tools\check_project_sources.py"
$importTool = Join-Path $workspacePath "tools\import_legacy_assets.py"
$validateTool = Join-Path $workspacePath "tools\validate_runtime.py"
$pakTool = Join-Path $workspacePath "tools\make_pak.py"
$zipTool = Join-Path $workspacePath "tools\make_release_zip.py"
$manifestTool = Join-Path $workspacePath "tools\release_manifest.py"
$collectLicensesTool = Join-Path $workspacePath "tools\collect_licenses.py"
$generateSbomTool = Join-Path $workspacePath "tools\generate_sbom.py"
$dependencyPolicy = Join-Path $workspacePath "docs\provenance\dependency-policy.json"
$completeImporterTool = Join-Path $workspacePath "tools\complete_importer_kit.ps1"
$packSource = Join-Path $workspacePath "pack"
$readmeSource = Join-Path $workspacePath "docs\release-readme.html"
$noticesSource = Join-Path $workspacePath "THIRD_PARTY_NOTICES.md"
$licenseSource = Join-Path $workspacePath "LICENSE"
$licenseScopeSource = Join-Path $workspacePath "LICENSE_SCOPE.md"
foreach ($required in @(
    $buildTool, $verifyBinaryTool, $checkProjectTool, $importTool, $validateTool,
    $pakTool, $zipTool, $manifestTool, $completeImporterTool, $packSource,
    $readmeSource, $noticesSource, $licenseSource, $licenseScopeSource,
    $collectLicensesTool, $generateSbomTool, $dependencyPolicy
)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required packaging input is missing: $required" }
}

$stageContainer = Join-Path $distPath "stage\windows-x64\$ArtifactLabel\$DistributionMode"
$stagePath = Join-Path $stageContainer "zaereo"
$workContainer = Join-Path $distPath "work\windows-x64\$ArtifactLabel\$DistributionMode"
$projectWork = Join-Path $workContainer "project"
$importWork = Join-Path $workContainer "verified-import"
$importManifest = Join-Path $workContainer "verified-import-asset-manifest.json"
$licenseWork = Join-Path $workContainer "dependency-evidence"
$binaryPath = Join-Path $workspacePath "build\Release\game_x64.dll"
$pdbPath = Join-Path $workspacePath "build\Release\game_x64.pdb"

$resolvedContent = ""
$resolvedAssetManifest = ""
$resolvedLegacy = ""
if ($DistributionMode -eq "local-full") {
    $explicitImported = $PSBoundParameters.ContainsKey("ImportedContentRoot") -and $ImportedContentRoot.Trim()
    $explicitLegacy = $PSBoundParameters.ContainsKey("ZaeroLegacyRoot") -and $ZaeroLegacyRoot.Trim()
    if ($explicitImported) {
        $resolvedContent = Resolve-PathByPrecedence $ImportedContentRoot "ZAEREO_CONTENT_ROOT" $configurationData @("zaeroImportedRoot", "zaereoContentRoot") $workspacePath "" "Imported content"
    }
    elseif ($explicitLegacy) {
        $resolvedLegacy = Resolve-PathByPrecedence $ZaeroLegacyRoot "ZAERO_LEGACY_ROOT" $configurationData @("zaeroLegacyRoot") $workspacePath "" "Legacy Zaero source"
    }
    elseif ($env:ZAEREO_CONTENT_ROOT) {
        $resolvedContent = Resolve-PathByPrecedence "" "ZAEREO_CONTENT_ROOT" $configurationData @("zaeroImportedRoot", "zaereoContentRoot") $workspacePath "" "Imported content"
    }
    elseif ($env:ZAERO_LEGACY_ROOT) {
        $resolvedLegacy = Resolve-PathByPrecedence "" "ZAERO_LEGACY_ROOT" $configurationData @("zaeroLegacyRoot") $workspacePath "" "Legacy Zaero source"
    }
    else {
        $configuredContent = Get-ConfigString $configurationData @("zaeroImportedRoot", "zaereoContentRoot")
        $configuredLegacy = Get-ConfigString $configurationData @("zaeroLegacyRoot")
        if ($configuredContent) {
            $resolvedContent = Resolve-PathByPrecedence "" "ZAEREO_CONTENT_ROOT" $configurationData @("zaeroImportedRoot", "zaereoContentRoot") $workspacePath "" "Imported content"
        }
        elseif ($configuredLegacy) {
            $resolvedLegacy = Resolve-PathByPrecedence "" "ZAERO_LEGACY_ROOT" $configurationData @("zaeroLegacyRoot") $workspacePath "" "Legacy Zaero source"
        }
        else {
            $defaultImported = Join-Path $workspacePath ".install\imported\zaereo"
            if (Test-Path -LiteralPath $defaultImported -PathType Container) {
                $resolvedContent = Get-FullPath $defaultImported
                Write-Host "Imported content found by safe read-only discovery: $resolvedContent"
            }
        }
    }
    if (-not $resolvedContent -and -not $resolvedLegacy) {
        throw "local-full requires a legitimate Zaero installation or a previously hash-verified import."
    }
    if ($resolvedContent) {
        if (-not (Test-Path -LiteralPath $resolvedContent -PathType Container)) {
            throw "Imported content directory does not exist: $resolvedContent"
        }
        $defaultAssetManifest = $resolvedContent.TrimEnd("\", "/") + "-asset-manifest.json"
        $resolvedAssetManifest = Resolve-PathByPrecedence $AssetManifest "ZAEREO_ASSET_MANIFEST" $configurationData @("zaeroAssetManifest", "zaereoAssetManifest") $workspacePath $defaultAssetManifest "Asset manifest"
        if (-not $resolvedAssetManifest -or -not (Test-Path -LiteralPath $resolvedAssetManifest -PathType Leaf)) {
            throw "local-full imported content requires its asset manifest proving the known retail PAK hashes."
        }
        Invoke-PythonTool $python $validateTool @(
            "--root", $resolvedContent,
            "--manifest", $resolvedAssetManifest,
            "--strict"
        )
    }
    elseif (-not (Test-Path -LiteralPath $resolvedLegacy -PathType Container)) {
        throw "Legacy Zaero source does not exist: $resolvedLegacy"
    }
    if ($resolvedLegacy) {
        # This is deliberately performed before the WhatIf return. It validates
        # all three known retail PAK hashes without writing imported content.
        Invoke-PythonTool $python $importTool @(
            "--source", $resolvedLegacy,
            "--output", $importWork,
            "--manifest", $importManifest,
            "--dry-run"
        )
    }
}

Write-Host "Package plan"
Write-Host "  version:      $version"
Write-Host "  commit:       $commit"
Write-Host "  mode:         $DistributionMode"
Write-Host "  dirty:        $isDirty"
Write-Host "  stage:        $stagePath"
Write-Host "  output root:  $distPath"
if ($DistributionMode -eq "importer-kit") {
    Write-Warning "Importer-kit archives contain no Zaero maps/media and are not playable until completed from a legitimate local installation."
}
else {
    Write-Warning "local-full output contains locally imported commercial media. It is permanently private and can never be published."
}
Write-Warning "Local verification output only. Remote publication is disabled until the machine-readable distribution policy and readiness gate are implemented and verified."
if ($WhatIfPreference) {
    Write-Host "WhatIf: preflight completed; build, staging, archives, and checksums were not written."
    return
}

if (-not $SkipBuild) {
    & $buildTool -WorkspaceRoot $workspacePath -Configuration Release
    if ($LASTEXITCODE -ne 0) { throw "Release build failed with exit code $LASTEXITCODE." }
}
if (-not (Test-Path -LiteralPath $binaryPath -PathType Leaf)) {
    throw "Release game DLL was not found: $binaryPath"
}
$vcpkgInstalledPath = if ($VcpkgInstalledRoot.Trim()) {
    Get-FullPath $VcpkgInstalledRoot $workspacePath
}
else {
    Join-Path $workspacePath "vcpkg_installed"
}
if (-not (Test-Path -LiteralPath $vcpkgInstalledPath -PathType Container)) {
    throw "Pinned vcpkg installed tree was not found: $vcpkgInstalledPath"
}

if (-not $SkipTests) {
    Invoke-PythonTool $python $checkProjectTool @()
    $pythonCommand = $python[0]
    $pythonPrefix = @($python | Select-Object -Skip 1)
    & $pythonCommand @pythonPrefix -m unittest discover -s (Join-Path $workspacePath "tests") -v
    if ($LASTEXITCODE -ne 0) { throw "Unit tests failed with exit code $LASTEXITCODE." }
    & $verifyBinaryTool -BinaryPath $binaryPath
    if ($LASTEXITCODE -ne 0) { throw "Binary export verification failed with exit code $LASTEXITCODE." }
}

New-Item -ItemType Directory -Path $distPath -Force | Out-Null
Reset-OwnedDirectory $distPath $workContainer
New-Item -ItemType Directory -Path $projectWork -Force | Out-Null
Invoke-PythonTool $python $collectLicensesTool @(
    "--policy", $dependencyPolicy,
    "--installed-root", $vcpkgInstalledPath,
    "--output", $licenseWork,
    "--source-date-epoch", [string]$sourceDateEpoch
)
$sbomWork = Join-Path $licenseWork "SBOM.spdx.json"
$sbomNamespace = "https://zaereo.invalid/sbom/$version/$commit/$DistributionMode/$sourceDateEpoch"
Invoke-PythonTool $python $generateSbomTool @(
    "--policy", $dependencyPolicy,
    "--license-manifest", (Join-Path $licenseWork "LICENSE-MANIFEST.json"),
    "--output", $sbomWork,
    "--document-name", "ZaeREo $version $DistributionMode Windows x64 SBOM",
    "--document-namespace", $sbomNamespace
)
if ($DistributionMode -eq "local-full") {
    if ($resolvedLegacy) {
        Invoke-PythonTool $python $importTool @(
            "--source", $resolvedLegacy,
            "--output", $importWork,
            "--manifest", $importManifest
        )
        $resolvedContent = $importWork
        $resolvedAssetManifest = $importManifest
        Invoke-PythonTool $python $validateTool @(
            "--root", $resolvedContent,
            "--manifest", $resolvedAssetManifest,
            "--strict"
        )
    }
    if (-not $resolvedLegacy) {
        Copy-TreeFiles $resolvedContent $importWork
    }
}
Copy-TreeFiles $packSource $projectWork @("README.md")
if ($DistributionMode -eq "local-full") {
    Assert-NoTreeCollisions $projectWork $importWork "Project/import runtime content"
    Invoke-PythonTool $python $validateTool @(
        "--root", $importWork,
        "--manifest", $resolvedAssetManifest,
        "--strict"
    )
}

$loosePaths = @()
if ($DistributionMode -eq "local-full") {
    $assetData = Get-Content -LiteralPath $resolvedAssetManifest -Raw | ConvertFrom-Json
    $loosePaths = @($assetData.required_loose_paths)
    if ($loosePaths.Count -eq 0 -or @($loosePaths | Where-Object { $_ -isnot [string] }).Count -ne 0) {
        throw "Verified asset manifest has no valid required_loose_paths list."
    }
}

Reset-OwnedDirectory $distPath $stageContainer
New-Item -ItemType Directory -Path $stagePath -Force | Out-Null
Copy-Item -LiteralPath $binaryPath -Destination (Join-Path $stagePath "game_x64.dll") -Force
Copy-Item -LiteralPath $readmeSource -Destination (Join-Path $stagePath "README.html") -Force
Copy-Item -LiteralPath $noticesSource -Destination (Join-Path $stagePath "THIRD_PARTY_NOTICES.md") -Force
Copy-Item -LiteralPath $licenseSource -Destination (Join-Path $stagePath "LICENSE.txt") -Force
Copy-Item -LiteralPath $licenseScopeSource -Destination (Join-Path $stagePath "LICENSE_SCOPE.md") -Force
Copy-TreeFiles $licenseWork $stagePath

$metadata = [ordered]@{
    schema_version = 1
    product = "ZaeREo"
    version = $version
    source_commit = $commit
    working_tree_dirty = $isDirty
    build_skipped = [bool]$SkipBuild
    tests_skipped = [bool]$SkipTests
    configuration = "Release"
    platform = "windows-x64"
    distribution_mode = $DistributionMode
    artifact_label = $ArtifactLabel
    source_date_epoch = $sourceDateEpoch
    dependency_policy = "zaereo-windows-x64-substrate-dependencies@1"
    sbom = "SBOM.spdx.json"
    license_manifest = "LICENSE-MANIFEST.json"
    publication_eligible = $false
    publication_block_reason = "Gameplay-tree remote publication is disabled until the machine-readable distribution policy and readiness gate are implemented and verified."
}
Write-Utf8NoBom (Join-Path $stagePath "BUILD-METADATA.json") (($metadata | ConvertTo-Json -Depth 4) + "`n")
$versionText = @(
    "ZaeREo $version",
    "Source commit: $commit",
    "Distribution mode: $DistributionMode",
    "Working tree dirty: $($isDirty.ToString().ToLowerInvariant())",
    "Build skipped: $([bool]$SkipBuild)",
    "Tests skipped: $([bool]$SkipTests)"
) -join "`n"
Write-Utf8NoBom (Join-Path $stagePath "VERSION.txt") ($versionText + "`n")

function New-DeterministicPak {
    param(
        [string]$SourceRoot,
        [string]$PakName,
        [string[]]$ExcludeRelative = @()
    )

    $firstPak = Join-Path $workContainer "$PakName-first.pak"
    $secondPak = Join-Path $stagePath $PakName
    $pakArguments = @($SourceRoot, $firstPak)
    foreach ($relative in $ExcludeRelative) { $pakArguments += @("--exclude", [string]$relative) }
    Invoke-PythonTool $python $pakTool $pakArguments
    $pakArguments[1] = $secondPak
    Invoke-PythonTool $python $pakTool $pakArguments
    $firstPakHash = (Get-FileHash -LiteralPath $firstPak -Algorithm SHA256).Hash.ToLowerInvariant()
    $secondPakHash = (Get-FileHash -LiteralPath $secondPak -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($firstPakHash -ne $secondPakHash) {
        throw "$PakName determinism check failed: $firstPakHash != $secondPakHash"
    }
    Invoke-PythonTool $python $validateTool @("--pak", $secondPak)
}

New-DeterministicPak $projectWork "pak0.pak"
if ($DistributionMode -eq "local-full") {
    New-DeterministicPak $importWork "pak1.pak" $loosePaths
    foreach ($relative in $loosePaths) {
        $source = Get-SafeDestination $importWork ([string]$relative).Replace("/", "\")
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
            throw "Required loose runtime asset is missing: $relative"
        }
        $target = Get-SafeDestination $stagePath ([string]$relative).Replace("/", "\")
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
    }
    Invoke-PythonTool $python $validateTool @(
        "--stage", $stagePath,
        "--manifest", $resolvedAssetManifest
    )
}

$runtimeOwnership = [ordered]@{
    schema_version = 1
    product = "ZaeREo runtime ownership"
    distribution_mode = $DistributionMode
    layers = @(
        [ordered]@{
            path = "pak0.pak"
            owner = "project"
            sha256 = (Get-FileHash -LiteralPath (Join-Path $stagePath "pak0.pak") -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    )
    generated_files = @(
        [ordered]@{
            path = "game_x64.dll"
            sha256 = (Get-FileHash -LiteralPath (Join-Path $stagePath "game_x64.dll") -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    )
}
if ($DistributionMode -eq "local-full") {
    $importedFiles = [Collections.Generic.List[object]]::new()
    $importedFiles.Add([ordered]@{
        path = "pak1.pak"
        owner = "imported"
        sha256 = (Get-FileHash -LiteralPath (Join-Path $stagePath "pak1.pak") -Algorithm SHA256).Hash.ToLowerInvariant()
    })
    foreach ($relative in $loosePaths) {
        $stagedLoose = Get-SafeDestination $stagePath ([string]$relative).Replace("/", "\\")
        $importedFiles.Add([ordered]@{
            path = ([string]$relative).Replace("\\", "/")
            owner = "imported-loose"
            sha256 = (Get-FileHash -LiteralPath $stagedLoose -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
    $runtimeOwnership.layers += @($importedFiles)
    $runtimeOwnership.import_manifest_sha256 = (Get-FileHash -LiteralPath $resolvedAssetManifest -Algorithm SHA256).Hash.ToLowerInvariant()
}
Write-Utf8NoBom (Join-Path $stagePath "RUNTIME-OWNERSHIP.json") (($runtimeOwnership | ConvertTo-Json -Depth 6) + "`n")

if ($DistributionMode -eq "importer-kit") {
    $toolStage = Join-Path $stagePath "tools"
    New-Item -ItemType Directory -Path $toolStage -Force | Out-Null
    foreach ($name in @(
        "complete_importer_kit.ps1", "import_legacy_assets.py", "make_pak.py", "validate_runtime.py"
    )) {
        Copy-Item -LiteralPath (Join-Path $workspacePath "tools\$name") -Destination (Join-Path $toolStage $name) -Force
    }
    $importInstructions = @"
ZaeREo importer kit
===================

This archive deliberately contains no Zaero maps, models, textures, sounds, or
cinematics. It is not playable until you complete it from a legitimate Zaero
installation. From this zaereo directory, run:

  pwsh -File .\tools\complete_importer_kit.ps1 -ZaeroLegacyRoot "D:\Games\Zaero"

The tool verifies the three known retail PAK SHA-256 hashes, never downloads
content, creates pak1.pak locally, and retains the nine required loose files.
Generated content is private local output; do not commit or redistribute it.
"@
    Write-Utf8NoBom (Join-Path $stagePath "IMPORT_ASSETS.txt") $importInstructions
}

$stageManifest = Join-Path $stagePath "MANIFEST.json"
Invoke-PythonTool $python $manifestTool @(
    "create", "--root", $stagePath, "--output", $stageManifest,
    "--version", $version, "--commit", $commit,
    "--distribution-mode", $DistributionMode
)
Invoke-PythonTool $python $manifestTool @(
    "verify", "--root", $stagePath, "--manifest", $stageManifest
)

$modeSuffix = if ($DistributionMode -eq "importer-kit") { "-importer-kit" } else { "" }
$archiveName = "zaereo-windows-x64-$ArtifactLabel$modeSuffix.zip"
$archivePath = Join-Path $distPath $archiveName
$archiveOutputs = @($archivePath, (Join-Path $distPath "$archiveName.manifest.json"))
foreach ($output in $archiveOutputs) {
    if ((Test-Path -LiteralPath $output) -and
        ((Get-Item -LiteralPath $output -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing to replace a reparse-point release output: $output"
    }
}
$verificationArchive = Join-Path $workContainer "verification.zip"
Invoke-PythonTool $python $zipTool @($stagePath, $verificationArchive, "--prefix", "zaereo")
Invoke-PythonTool $python $zipTool @($stagePath, $archivePath, "--prefix", "zaereo")
$firstArchiveHash = (Get-FileHash -LiteralPath $verificationArchive -Algorithm SHA256).Hash.ToLowerInvariant()
$archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($firstArchiveHash -ne $archiveHash) {
    throw "ZIP determinism check failed: $firstArchiveHash != $archiveHash"
}

$externalManifestPath = Join-Path $distPath "$archiveName.manifest.json"
Copy-Item -LiteralPath $stageManifest -Destination $externalManifestPath -Force
$artifactPaths = [Collections.Generic.List[string]]::new()
$artifactPaths.Add($archivePath)
$artifactPaths.Add($externalManifestPath)
$symbolsPath = ""
if ($IncludeSymbols) {
    if (-not (Test-Path -LiteralPath $pdbPath -PathType Leaf)) {
        throw "-IncludeSymbols was requested but no Release PDB exists: $pdbPath"
    }
    $symbolsStage = Join-Path $workContainer "symbols"
    New-Item -ItemType Directory -Path $symbolsStage -Force | Out-Null
    Copy-Item -LiteralPath $pdbPath -Destination (Join-Path $symbolsStage "game_x64.pdb") -Force
    $symbolsPath = Join-Path $distPath "zaereo-windows-x64-$ArtifactLabel-symbols.zip"
    if ((Test-Path -LiteralPath $symbolsPath) -and
        ((Get-Item -LiteralPath $symbolsPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing to replace a reparse-point symbols output: $symbolsPath"
    }
    Invoke-PythonTool $python $zipTool @($symbolsStage, $symbolsPath, "--prefix", "zaereo-symbols")
    $artifactPaths.Add($symbolsPath)
}

$checksumPath = Join-Path $distPath "SHA256SUMS-$ArtifactLabel$modeSuffix.txt"
if ((Test-Path -LiteralPath $checksumPath) -and
    ((Get-Item -LiteralPath $checksumPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw "Refusing to replace a reparse-point checksum output: $checksumPath"
}
$checksumLines = foreach ($artifact in @($artifactPaths | Sort-Object { Split-Path -Leaf $_ })) {
    $hash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $(Split-Path -Leaf $artifact)"
}
Write-Utf8NoBom $checksumPath (($checksumLines -join "`n") + "`n")

Set-GitHubOutput "archive_path" $archivePath
Set-GitHubOutput "archive_name" $archiveName
Set-GitHubOutput "archive_sha256" $archiveHash
Set-GitHubOutput "manifest_path" $externalManifestPath
Set-GitHubOutput "checksum_path" $checksumPath
Set-GitHubOutput "symbols_path" $symbolsPath
Set-GitHubOutput "version" $version
Set-GitHubOutput "source_commit" $commit
Set-GitHubOutput "distribution_mode" $DistributionMode

Write-Host "Staged:   $stagePath"
Write-Host "Archive:  $archivePath"
Write-Host "SHA256:   $archiveHash"
Write-Host "Manifest: $externalManifestPath"
Write-Host "Checksums: $checksumPath"
if ($symbolsPath) { Write-Host "Symbols:  $symbolsPath" }
