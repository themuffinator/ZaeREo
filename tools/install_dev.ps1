[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Medium")]
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$EngineRoot = "",
    [string]$UserRoot = "",
    [string]$GameRoot = "",
    [string]$ContentRoot = "",
    [string]$AssetManifest = "",
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Debug",
    [switch]$SkipBuild,
    [switch]$NoPak,
    [switch]$Link
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "zaereo_paths.ps1")

function Assert-StrictChildPath {
    param(
        [Parameter(Mandatory = $true)][string]$Parent,
        [Parameter(Mandatory = $true)][string]$Child,
        [string]$Description = "path"
    )

    $parentPath = (Get-ZaeREoFullPath $Parent).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $childPath = (Get-ZaeREoFullPath $Child).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $prefix = $parentPath + [IO.Path]::DirectorySeparatorChar
    if (-not $childPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Description must remain below '$parentPath': $childPath"
    }
    return $childPath
}


function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        return @($launcher.Source, "-3")
    }
    throw "Python 3 was not found in PATH. Run tools/bootstrap.ps1 first."
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

function Reset-OwnedDirectory {
    param([string]$OwnedRoot, [string]$Target)

    $safeTarget = Assert-StrictChildPath $OwnedRoot $Target "generated directory"
    if (Test-Path -LiteralPath $safeTarget) {
        $item = Get-Item -LiteralPath $safeTarget -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to recursively remove a reparse point: $safeTarget"
        }
        Remove-Item -LiteralPath $safeTarget -Recurse -Force
    }
    New-Item -ItemType Directory -Path $safeTarget -Force | Out-Null
}

function Get-SafeRelativePath {
    param([string]$RelativePath, [string]$Root)

    if (-not $RelativePath -or [IO.Path]::IsPathRooted($RelativePath) -or
        $RelativePath.Contains(":") -or $RelativePath -match '(^|[\\/])\.\.([\\/]|$)') {
        throw "Unsafe managed relative path: '$RelativePath'"
    }
    $candidate = Get-ZaeREoFullPath (Join-Path $Root $RelativePath)
    [void](Assert-StrictChildPath $Root $candidate "managed file")
    return $candidate
}

function Copy-TreeFiles {
    param([string]$Source, [string]$Destination, [string[]]$ExcludeRelative = @())

    $sourcePath = Get-ZaeREoFullPath $Source
    $destinationPath = Get-ZaeREoFullPath $Destination
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
            throw "Refusing to copy a reparse point: $($file.FullName)"
        }
        $relative = [IO.Path]::GetRelativePath($sourcePath, $file.FullName)
        $normalized = $relative.Replace("\", "/")
        if ($excluded.ContainsKey($normalized.ToLowerInvariant())) {
            continue
        }
        $target = Get-SafeRelativePath $relative $destinationPath
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target -Force
    }
}

function Get-ManagedFiles {
    param([string]$Root)

    $rootPath = Get-ZaeREoFullPath $Root
    $files = foreach ($file in Get-ChildItem -LiteralPath $rootPath -File -Recurse -Force) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Managed stage contains a reparse point: $($file.FullName)"
        }
        [IO.Path]::GetRelativePath($rootPath, $file.FullName).Replace("\", "/")
    }
    return @($files | Sort-Object)
}

function Install-ManagedCopy {
    param([string]$Stage, [string]$Destination)

    $stagePath = Get-ZaeREoFullPath $Stage
    $destinationPath = Get-ZaeREoFullPath $Destination
    $manifestName = ".zaereo-managed-files.json"
    $manifestPath = Join-Path $destinationPath $manifestName
    $previous = @()
    if (Test-Path -LiteralPath $destinationPath) {
        $destinationItem = Get-Item -LiteralPath $destinationPath -Force
        if ($destinationItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Copy mode will not replace a linked mod directory: $destinationPath"
        }
        if (-not $destinationItem.PSIsContainer) {
            throw "Developer install target is not a directory: $destinationPath"
        }
        if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
            try {
                $oldManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
                $previous = @($oldManifest.files)
            }
            catch {
                throw "Previous developer install manifest is invalid; no files were removed: $manifestPath"
            }
        }
        elseif (@(Get-ChildItem -LiteralPath $destinationPath -Force).Count -gt 0) {
            throw "Target is non-empty but has no ZaeREo managed-file manifest: $destinationPath"
        }
    }
    else {
        New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
    }

    $current = Get-ManagedFiles $stagePath
    $currentSet = @{}
    foreach ($relative in $current) {
        $currentSet[$relative.ToLowerInvariant()] = $true
    }
    foreach ($relative in $previous) {
        if ($relative -isnot [string]) {
            throw "Previous developer install manifest contains a non-string path."
        }
        $target = Get-SafeRelativePath $relative $destinationPath
        if (-not $currentSet.ContainsKey($relative.ToLowerInvariant()) -and
            (Test-Path -LiteralPath $target -PathType Leaf)) {
            Remove-Item -LiteralPath $target -Force
        }
    }

    foreach ($relative in $current) {
        $source = Get-SafeRelativePath $relative $stagePath
        $target = Get-SafeRelativePath $relative $destinationPath
        if ((Test-Path -LiteralPath $target) -and
            -not (@($previous) -contains $relative) -and
            $relative -ne $manifestName) {
            throw "Refusing to overwrite an unmanaged file: $target"
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
    }
}

$workspacePath = Get-ZaeREoFullPath $WorkspaceRoot
if (-not (Test-Path -LiteralPath $workspacePath -PathType Container)) {
    throw "Workspace does not exist: $workspacePath"
}
$configurationData = Get-ZaeREoLocalConfiguration $workspacePath
$installRoots = Resolve-ZaeREoInstallRoots `
    -WorkspacePath $workspacePath `
    -Configuration $configurationData `
    -EngineRoot $EngineRoot `
    -UserRoot $UserRoot `
    -GameRoot $GameRoot
$enginePath = $installRoots.EngineRoot
$userRootPath = $installRoots.UserRoot

$defaultContent = Join-Path $workspacePath ".install\imported\zaereo"
$contentPath = Resolve-ZaeREoPath `
    -ExplicitValue $ContentRoot `
    -EnvironmentNames @("ZAEREO_CONTENT_ROOT") `
    -Configuration $configurationData `
    -ConfigurationNames @("zaeroImportedRoot", "zaereoContentRoot") `
    -WorkspacePath $workspacePath `
    -Discovery { if (Test-Path -LiteralPath $defaultContent -PathType Container) { $defaultContent } else { "" } } `
    -Description "Verified imported content root"
if (-not $contentPath -or -not (Test-Path -LiteralPath $contentPath -PathType Container)) {
    throw "Verified imported content was not found. Run import_legacy_assets.py or pass -ContentRoot."
}

$defaultManifest = $contentPath.TrimEnd("\", "/") + "-asset-manifest.json"
$manifestPath = Resolve-ZaeREoPath `
    -ExplicitValue $AssetManifest `
    -EnvironmentNames @("ZAEREO_ASSET_MANIFEST") `
    -Configuration $configurationData `
    -ConfigurationNames @("zaeroAssetManifest", "zaereoAssetManifest") `
    -WorkspacePath $workspacePath `
    -Discovery { if (Test-Path -LiteralPath $defaultManifest -PathType Leaf) { $defaultManifest } else { "" } } `
    -Description "Verified asset manifest"
if (-not $manifestPath -or -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "The importer asset manifest is required to prove the known retail PAK hashes."
}

$python = Get-PythonCommand
$validateTool = Join-Path $workspacePath "tools\validate_runtime.py"
$pakTool = Join-Path $workspacePath "tools\make_pak.py"
$buildTool = Join-Path $workspacePath "tools\build_game.ps1"
$packSource = Join-Path $workspacePath "pack"
$binaryPath = Join-Path $workspacePath "build\$Configuration\game_x64.dll"
foreach ($required in @($validateTool, $pakTool, $buildTool, $packSource)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required repository input is missing: $required"
    }
}

Write-Host "Validating imported content and retail provenance manifest..."
Invoke-PythonTool $python $validateTool @(
    "--root", $contentPath,
    "--manifest", $manifestPath,
    "--strict"
)

if (-not $SkipBuild) {
    if ($PSCmdlet.ShouldProcess($binaryPath, "Build $Configuration game DLL")) {
        & $buildTool -WorkspaceRoot $workspacePath -Configuration $Configuration
        if ($LASTEXITCODE -ne 0) {
            throw "Game build failed with exit code $LASTEXITCODE."
        }
    }
}
if (-not $WhatIfPreference -and -not (Test-Path -LiteralPath $binaryPath -PathType Leaf)) {
    throw "Built game DLL was not found: $binaryPath"
}

$installRoot = Join-Path $workspacePath ".install"
$workRoot = Join-Path $installRoot "dev-work"
$contentWork = Join-Path $workRoot "content"
$stagePath = Join-Path $installRoot "zaereo"
$targetPath = $installRoots.TargetPath
[void](Assert-StrictChildPath $userRootPath $targetPath "mod install target")

if ($WhatIfPreference) {
    Write-Host "WhatIf plan: merge verified imported content with repository pack content."
    Write-Host "WhatIf plan: stage $binaryPath and runtime content at $stagePath."
    Write-Host "WhatIf plan: install only managed files into $targetPath."
    return
}

if ($PSCmdlet.ShouldProcess($workRoot, "Recreate owned developer work directory")) {
    New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
    Reset-OwnedDirectory $installRoot $workRoot
    New-Item -ItemType Directory -Path $contentWork -Force | Out-Null
    Copy-TreeFiles $contentPath $contentWork
    Copy-TreeFiles $packSource $contentWork @("README.md")
}

$assetData = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$loosePaths = @($assetData.required_loose_paths)
if ($loosePaths.Count -eq 0 -or @($loosePaths | Where-Object { $_ -isnot [string] }).Count -ne 0) {
    throw "Importer manifest does not declare the required loose runtime paths."
}

if ($PSCmdlet.ShouldProcess($stagePath, "Recreate owned developer stage")) {
    Reset-OwnedDirectory $installRoot $stagePath
    Copy-Item -LiteralPath $binaryPath -Destination (Join-Path $stagePath "game_x64.dll") -Force
    if ($NoPak) {
        Copy-TreeFiles $contentWork $stagePath
    }
    else {
        $pakArguments = @($contentWork, (Join-Path $stagePath "pak0.pak"))
        foreach ($relative in $loosePaths) {
            $pakArguments += @("--exclude", ([string]$relative))
        }
        Invoke-PythonTool $python $pakTool $pakArguments
        foreach ($relative in $loosePaths) {
            $source = Get-SafeRelativePath ([string]$relative) $contentWork
            if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
                throw "Required loose runtime file is missing: $relative"
            }
            $target = Get-SafeRelativePath ([string]$relative) $stagePath
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            Copy-Item -LiteralPath $source -Destination $target -Force
        }
    }

    $commit = (& git -C $workspacePath rev-parse HEAD 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $commit) {
        $commit = "unknown"
    }
    @(
        "ZaeREo development installation",
        "Configuration: $Configuration",
        "Source commit: $commit",
        "Content provenance: known Zaero retail PAK hashes verified",
        "Generated UTC: $([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
    ) | Set-Content -LiteralPath (Join-Path $stagePath "DEVELOPMENT.txt") -Encoding utf8

    $managedFiles = @(Get-ManagedFiles $stagePath) + ".zaereo-managed-files.json"
    $managedManifest = [ordered]@{
        schema_version = 1
        product = "ZaeREo developer install"
        files = @($managedFiles | Sort-Object -Unique)
    }
    $managedManifest | ConvertTo-Json -Depth 4 | Set-Content `
        -LiteralPath (Join-Path $stagePath ".zaereo-managed-files.json") -Encoding utf8
}

if ($Link) {
    if (Test-Path -LiteralPath $targetPath) {
        $targetItem = Get-Item -LiteralPath $targetPath -Force
        if (-not ($targetItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Link mode will not replace a real directory: $targetPath"
        }
        $linkTarget = @($targetItem.Target)[0]
        if (-not $linkTarget -or (Get-ZaeREoFullPath ([string]$linkTarget) $userRootPath) -ne (Get-ZaeREoFullPath $stagePath)) {
            throw "Existing link does not point to the owned ZaeREo stage: $targetPath"
        }
        Write-Host "Developer link already points to $stagePath"
    }
    elseif ($PSCmdlet.ShouldProcess($targetPath, "Create directory junction to $stagePath")) {
        New-Item -ItemType Junction -Path $targetPath -Target $stagePath | Out-Null
    }
}
elseif ($PSCmdlet.ShouldProcess($targetPath, "Update ZaeREo-managed developer files")) {
    Install-ManagedCopy $stagePath $targetPath
}

Write-Host "Developer stage: $stagePath"
Write-Host "Engine/data root: $enginePath (read-only)"
Write-Host "User-data root:   $userRootPath"
Write-Host "Installed mod:    $targetPath"
Write-Host "Launch with:      +set game zaereo +exec zaerostart.cfg"
