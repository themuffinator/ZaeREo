[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Medium")]
param(
    [string]$ZaeroLegacyRoot = "",
    [string]$ModRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$Overwrite
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-FullPath {
    param([string]$Path, [string]$Base)
    $expanded = [Environment]::ExpandEnvironmentVariables($Path.Trim())
    if (-not [IO.Path]::IsPathRooted($expanded)) {
        $expanded = Join-Path $Base $expanded
    }
    return [IO.Path]::GetFullPath($expanded)
}

function Assert-ChildPath {
    param([string]$Parent, [string]$Child)
    $parentPath = (Get-FullPath $Parent $Parent).TrimEnd("\", "/")
    $childPath = (Get-FullPath $Child $Parent).TrimEnd("\", "/")
    if (-not $childPath.StartsWith($parentPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes the selected ZaeREo directory: $childPath"
    }
    return $childPath
}

function Invoke-Python {
    param([string]$Script, [string[]]$Arguments)
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source $Script @Arguments
    }
    else {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw "Python 3 was not found in PATH."
        }
        & $launcher.Source -3 $Script @Arguments
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python tool failed with exit code ${LASTEXITCODE}: $Script"
    }
}

$modPath = Get-FullPath $ModRoot (Get-Location).Path
if (-not (Test-Path -LiteralPath $modPath -PathType Container)) {
    throw "ZaeREo directory does not exist: $modPath"
}
$localConfigPath = Join-Path $modPath ".zaereo.local.json"
$localValue = ""
if (Test-Path -LiteralPath $localConfigPath -PathType Leaf) {
    try {
        $localConfig = Get-Content -LiteralPath $localConfigPath -Raw | ConvertFrom-Json
        $property = $localConfig.PSObject.Properties["zaeroLegacyRoot"]
        if ($null -ne $property -and $property.Value -is [string]) {
            $localValue = $property.Value.Trim()
        }
    }
    catch {
        throw "Could not parse '$localConfigPath': $($_.Exception.Message)"
    }
}

$legacyValue = if ($ZaeroLegacyRoot.Trim()) {
    Write-Host "Zaero source resolved from explicit parameter."
    $ZaeroLegacyRoot
}
elseif ($env:ZAERO_LEGACY_ROOT -and $env:ZAERO_LEGACY_ROOT.Trim()) {
    Write-Host "Zaero source resolved from ZAERO_LEGACY_ROOT."
    $env:ZAERO_LEGACY_ROOT
}
elseif ($localValue) {
    Write-Host "Zaero source resolved from ignored .zaereo.local.json."
    $localValue
}
else {
    throw "Pass -ZaeroLegacyRoot, set ZAERO_LEGACY_ROOT, or configure zaeroLegacyRoot. No content is downloaded."
}
$legacyPath = Get-FullPath $legacyValue $modPath
if (-not (Test-Path -LiteralPath $legacyPath -PathType Container)) {
    throw "Legacy Zaero directory does not exist: $legacyPath"
}

$importTool = Join-Path $PSScriptRoot "import_legacy_assets.py"
$pakTool = Join-Path $PSScriptRoot "make_pak.py"
$validateTool = Join-Path $PSScriptRoot "validate_runtime.py"
foreach ($tool in @($importTool, $pakTool, $validateTool)) {
    if (-not (Test-Path -LiteralPath $tool -PathType Leaf)) {
        throw "Importer kit is incomplete: $tool"
    }
}

$workPath = Assert-ChildPath $modPath (Join-Path $modPath ".zaereo-import-work")
$manifestPath = Assert-ChildPath $modPath (Join-Path $modPath ".zaereo-asset-manifest.json")
$pakPath = Assert-ChildPath $modPath (Join-Path $modPath "pak1.pak")
$verificationPak = Assert-ChildPath $modPath (Join-Path $modPath ".zaereo-pak1-verification.pak")

Write-Host "Verifying the known Zaero retail PAK hashes before writing content..."
Invoke-Python $importTool @(
    "--source", $legacyPath,
    "--output", $workPath,
    "--manifest", $manifestPath,
    "--dry-run"
)

if ($WhatIfPreference) {
    Write-Host "WhatIf plan: create a private import workspace below $modPath."
    Write-Host "WhatIf plan: build deterministic pak1.pak and copy nine required loose assets."
    return
}

if (Test-Path -LiteralPath $pakPath -PathType Leaf) {
    if (-not $Overwrite) {
        throw "pak1.pak already exists. Pass -Overwrite to replace this importer-managed package."
    }
}
if (Test-Path -LiteralPath $workPath) {
    if (-not $Overwrite) {
        throw "A prior private import workspace exists. Pass -Overwrite to remove only this importer-owned path: $workPath"
    }
    $workItem = Get-Item -LiteralPath $workPath -Force
    if ($workItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing to remove a reparse point: $workPath"
    }
    if ($PSCmdlet.ShouldProcess($workPath, "Remove prior private import workspace")) {
        Remove-Item -LiteralPath $workPath -Recurse -Force
    }
}
if (Test-Path -LiteralPath $verificationPak) {
    throw "Refusing to overwrite unexpected verification scratch: $verificationPak"
}

try {
    if ($PSCmdlet.ShouldProcess($workPath, "Import hash-verified Zaero runtime content")) {
        Invoke-Python $importTool @(
            "--source", $legacyPath,
            "--output", $workPath,
            "--manifest", $manifestPath
        )
        Invoke-Python $validateTool @(
            "--root", $workPath,
            "--manifest", $manifestPath,
            "--strict"
        )
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $loosePaths = @($manifest.required_loose_paths)
    if ($loosePaths.Count -eq 0 -or @($loosePaths | Where-Object { $_ -isnot [string] }).Count -ne 0) {
        throw "Verified importer manifest has no valid required_loose_paths list."
    }
    $pakArguments = @($workPath, $verificationPak)
    foreach ($relative in $loosePaths) {
        $pakArguments += @("--exclude", [string]$relative)
    }
    Invoke-Python $pakTool $pakArguments
    $pakArguments[1] = $pakPath
    Invoke-Python $pakTool $pakArguments
    $firstHash = (Get-FileHash -LiteralPath $verificationPak -Algorithm SHA256).Hash
    $secondHash = (Get-FileHash -LiteralPath $pakPath -Algorithm SHA256).Hash
    if ($firstHash -ne $secondHash) {
        throw "Deterministic PAK verification failed: $firstHash != $secondHash"
    }

    foreach ($relative in $loosePaths) {
        $relativePath = ([string]$relative).Replace("/", [IO.Path]::DirectorySeparatorChar)
        $source = Assert-ChildPath $workPath (Join-Path $workPath $relativePath)
        $target = Assert-ChildPath $modPath (Join-Path $modPath $relativePath)
        if ((Test-Path -LiteralPath $target) -and -not $Overwrite) {
            throw "Loose runtime path already exists. Pass -Overwrite to replace importer-managed files: $target"
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
    }

    @(
        "ZaeREo importer kit completed locally.",
        "Known Zaero retail PAK hashes: verified",
        "pak1.pak SHA-256: $($secondHash.ToLowerInvariant())",
        "This generated content must not be committed or redistributed without permission."
    ) | Set-Content -LiteralPath (Join-Path $modPath "IMPORT-COMPLETE.txt") -Encoding utf8
}
finally {
    if (Test-Path -LiteralPath $verificationPak -PathType Leaf) {
        Remove-Item -LiteralPath $verificationPak -Force
    }
    if (Test-Path -LiteralPath $workPath) {
        $workItem = Get-Item -LiteralPath $workPath -Force
        if ($workItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Private import workspace became a reparse point; refusing recursive cleanup: $workPath"
        }
        Remove-Item -LiteralPath $workPath -Recurse -Force
    }
}

Write-Host "Local content import is complete: $pakPath"
Write-Host "SHA256 $($secondHash.ToLowerInvariant())"
Write-Host "For any verified development/debug/validation launch, use the checkout's tools/run_game.ps1; do not bypass its window-before-mod/map safety check."
