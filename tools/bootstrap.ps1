[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$VcpkgRoot = "",
    [string]$Triplet = "x64-windows-static",
    [switch]$SkipDependencies
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "zaereo_paths.ps1")

function Resolve-CommandPath {
    param([Parameter(Mandatory)][string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Required command '$Name' was not found."
    }
    return $command.Source
}

$workspacePath = (Resolve-Path $WorkspaceRoot).Path
$manifestPath = Join-Path $workspacePath "vcpkg.json"
if (-not (Test-Path $manifestPath)) {
    throw "vcpkg manifest not found: $manifestPath"
}

$git = Resolve-CommandPath "git"
$gitLfs = Resolve-CommandPath "git-lfs"
$python = Resolve-CommandPath "python"

$pythonVersion = & $python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to execute Python at $python"
}
$pythonMajorMinor = [version](($pythonVersion -split '\.')[0..1] -join '.')
if ($pythonMajorMinor -lt [version]"3.11") {
    throw "Python 3.11 or newer is required; found $pythonVersion at $python"
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    throw "vswhere.exe was not found at $vswhere. Install Visual Studio 2022 Build Tools with Desktop C++."
}

$msbuild = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" |
    Select-Object -First 1
if (-not $msbuild) {
    throw "MSBuild was not found by vswhere. Install the Visual Studio 2022 C++ workload."
}

$configurationData = Get-ZaeREoLocalConfiguration $workspacePath
$vcpkgRoot = Resolve-ZaeREoVcpkgRoot `
    -ExplicitValue $VcpkgRoot `
    -Configuration $configurationData `
    -WorkspacePath $workspacePath
$vcpkg = Join-Path $vcpkgRoot "vcpkg.exe"
$installRoot = Join-Path $workspacePath "vcpkg_installed"

Write-Host "ZaeREo bootstrap environment"
Write-Host "  Workspace : $workspacePath"
Write-Host "  Git       : $git"
Write-Host "  Git LFS   : $gitLfs"
Write-Host "  Python    : $python ($pythonVersion)"
Write-Host "  MSBuild   : $msbuild"
Write-Host "  vcpkg     : $vcpkgRoot"
Write-Host "  Triplet   : $Triplet"

if (-not $SkipDependencies) {
    & $vcpkg install `
        "--triplet=$Triplet" `
        "--x-manifest-root=$workspacePath" `
        "--x-install-root=$installRoot"
    if ($LASTEXITCODE -ne 0) {
        throw "vcpkg dependency installation failed with exit code $LASTEXITCODE"
    }
}

Write-Host "Bootstrap checks completed successfully."
