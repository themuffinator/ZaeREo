[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [ValidateSet("x64")]
    [string]$Platform = "x64",
    [string]$Triplet = "x64-windows-static",
    [string]$VcpkgRoot = "",
    [switch]$SkipBootstrap,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "zaereo_paths.ps1")

$workspacePath = (Resolve-Path $WorkspaceRoot).Path
$solutionPath = Join-Path $workspacePath "src\game.sln"
if (-not (Test-Path $solutionPath)) {
    throw "Solution not found: $solutionPath"
}

$configurationData = Get-ZaeREoLocalConfiguration $workspacePath
$resolvedVcpkgRoot = Resolve-ZaeREoVcpkgRoot `
    -ExplicitValue $VcpkgRoot `
    -Configuration $configurationData `
    -WorkspacePath $workspacePath

if (-not $SkipBootstrap) {
    & (Join-Path $PSScriptRoot "bootstrap.ps1") `
        -WorkspaceRoot $workspacePath `
        -VcpkgRoot $resolvedVcpkgRoot `
        -Triplet $Triplet
    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap failed with exit code $LASTEXITCODE"
    }
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    throw "vswhere.exe was not found at $vswhere"
}

$msbuild = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" |
    Select-Object -First 1
if (-not $msbuild) {
    throw "MSBuild.exe was not found by vswhere."
}

$target = if ($Rebuild) { "Rebuild" } else { "Build" }
$outputPath = Join-Path $workspacePath "build\$Configuration\game_x64.dll"

Write-Host "Building $solutionPath ($Configuration|$Platform, target $target)"
& $msbuild `
    $solutionPath `
    /m `
    "/t:$target" `
    "/p:Configuration=$Configuration" `
    "/p:Platform=$Platform" `
    "/p:VcpkgRoot=$resolvedVcpkgRoot\" `
    "/p:VcpkgManifestRoot=$workspacePath\" `
    "/p:VcpkgInstalledDir=$workspacePath\vcpkg_installed\" `
    "/p:VcpkgTriplet=$Triplet" `
    /nologo

if ($LASTEXITCODE -ne 0) {
    throw "MSBuild failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $outputPath)) {
    throw "Build completed but expected DLL was not found: $outputPath"
}

$dll = Get-Item $outputPath
Write-Host "Built $($dll.FullName) ($($dll.Length) bytes)"
Write-Output $dll.FullName
