[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BinaryPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$resolvedBinary = (Resolve-Path $BinaryPath).Path
$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    throw "vswhere.exe was not found at $vswhere"
}

$dumpbin = & $vswhere -latest -products * -find "VC\Tools\MSVC\**\bin\Hostx64\x64\dumpbin.exe" |
    Select-Object -First 1
if (-not $dumpbin) {
    throw "dumpbin.exe was not found by vswhere"
}

$exports = (& $dumpbin /exports $resolvedBinary | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw "dumpbin failed with exit code $LASTEXITCODE"
}

foreach ($required in @("GetGameAPI", "GetCGameAPI")) {
    if ($exports -notmatch "(?m)^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+$required(?:\s|$)") {
        throw "Required export '$required' was not found in $resolvedBinary"
    }
}

$binary = Get-Item $resolvedBinary
$hash = Get-FileHash $resolvedBinary -Algorithm SHA256
Write-Host "Verified game and cgame exports in $($binary.FullName)"
Write-Host "SHA-256: $($hash.Hash)"

