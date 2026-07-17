Set-StrictMode -Version Latest

function Get-ZaeREoFullPath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Base = ""
    )

    $expanded = [Environment]::ExpandEnvironmentVariables($Path.Trim())
    if (-not [IO.Path]::IsPathRooted($expanded)) {
        if (-not $Base) {
            throw "A base directory is required for relative path '$Path'."
        }
        $expanded = Join-Path $Base $expanded
    }
    return [IO.Path]::GetFullPath($expanded)
}

function Get-ZaeREoLocalConfiguration {
    param([Parameter(Mandatory = $true)][string]$WorkspacePath)

    $configPath = Join-Path $WorkspacePath ".zaereo.local.json"
    if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
        return $null
    }
    try {
        $configuration = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    }
    catch {
        throw "Could not parse local path configuration '$configPath': $($_.Exception.Message)"
    }
    $schemaVersion = $configuration.PSObject.Properties["schemaVersion"]
    if ($null -ne $schemaVersion -and $schemaVersion.Value -ne 1) {
        throw "Unsupported .zaereo.local.json schemaVersion '$($schemaVersion.Value)'; expected 1."
    }
    if ($null -eq $schemaVersion) {
        Write-Warning "Legacy .zaereo.local.json has no schemaVersion; migrate from q2RereleaseRoot to the split engine/user keys."
    }
    Write-Host "Using ignored local path configuration: $configPath"
    return $configuration
}

function Get-ZaeREoConfigurationValue {
    param(
        [object]$Configuration,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $Configuration) {
        return ""
    }
    foreach ($name in $Names) {
        $property = $Configuration.PSObject.Properties[$name]
        if ($null -ne $property -and $property.Value -is [string] -and $property.Value.Trim()) {
            return $property.Value.Trim()
        }
    }
    return ""
}

function Resolve-ZaeREoPath {
    param(
        [string]$ExplicitValue = "",
        [string[]]$EnvironmentNames = @(),
        [object]$Configuration,
        [string[]]$ConfigurationNames = @(),
        [Parameter(Mandatory = $true)][string]$WorkspacePath,
        [scriptblock]$Discovery,
        [Parameter(Mandatory = $true)][string]$Description,
        [string[]]$LegacyEnvironmentNames = @(),
        [string[]]$LegacyConfigurationNames = @()
    )

    if ($ExplicitValue.Trim()) {
        $resolved = Get-ZaeREoFullPath $ExplicitValue $WorkspacePath
        Write-Host "$Description resolved from explicit parameter: $resolved"
        return $resolved
    }
    foreach ($name in $EnvironmentNames) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value -and $value.Trim()) {
            $resolved = Get-ZaeREoFullPath $value $WorkspacePath
            Write-Host "$Description resolved from ${name}: $resolved"
            return $resolved
        }
    }
    foreach ($name in $LegacyEnvironmentNames) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value -and $value.Trim()) {
            $resolved = Get-ZaeREoFullPath $value $WorkspacePath
            Write-Warning "$name is a legacy alias for $Description; migrate to $($EnvironmentNames -join ', ')."
            return $resolved
        }
    }
    foreach ($name in $ConfigurationNames) {
        $value = Get-ZaeREoConfigurationValue $Configuration @($name)
        if ($value) {
            $resolved = Get-ZaeREoFullPath $value $WorkspacePath
            Write-Host "$Description resolved from .zaereo.local.json '$name': $resolved"
            return $resolved
        }
    }
    foreach ($name in $LegacyConfigurationNames) {
        $value = Get-ZaeREoConfigurationValue $Configuration @($name)
        if ($value) {
            $resolved = Get-ZaeREoFullPath $value $WorkspacePath
            Write-Warning ".zaereo.local.json '$name' is a legacy alias for $Description; migrate to $($ConfigurationNames -join ', ')."
            return $resolved
        }
    }
    if ($null -ne $Discovery) {
        $discovered = & $Discovery
        if ($discovered) {
            $resolved = Get-ZaeREoFullPath ([string]$discovered) $WorkspacePath
            Write-Host "$Description safely discovered (read-only): $resolved"
            return $resolved
        }
    }
    return ""
}

function Find-ZaeREoRereleaseRoot {
    $candidates = [Collections.Generic.List[string]]::new()
    $registryKeys = @(
        "HKCU:\Software\Valve\Steam",
        "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam",
        "HKLM:\SOFTWARE\Valve\Steam"
    )
    foreach ($key in $registryKeys) {
        try {
            $steam = Get-ItemProperty -LiteralPath $key -ErrorAction Stop
            foreach ($propertyName in @("SteamPath", "InstallPath")) {
                $property = $steam.PSObject.Properties[$propertyName]
                if ($null -ne $property -and $property.Value) {
                    $candidates.Add((Join-Path ([string]$property.Value) "steamapps\common\Quake 2\rerelease"))
                }
            }
        }
        catch {
            # Discovery is deliberately read-only and best-effort.
        }
    }
    if (${env:ProgramFiles(x86)}) {
        $candidates.Add((Join-Path ${env:ProgramFiles(x86)} "Steam\steamapps\common\Quake 2\rerelease"))
    }
    foreach ($candidate in $candidates) {
        if ((Test-Path -LiteralPath $candidate -PathType Container) -and
            (Test-Path -LiteralPath (Join-Path $candidate "baseq2") -PathType Container)) {
            return (Get-ZaeREoFullPath $candidate)
        }
    }
    return ""
}

function Get-ZaeREoDefaultUserRoot {
    $profile = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
    if (-not $profile) {
        $profile = $env:USERPROFILE
    }
    if (-not $profile) {
        throw "The current user profile could not be resolved. Pass -UserRoot explicitly."
    }
    return (Join-Path $profile "Saved Games\Nightdive Studios\Quake II")
}

function Resolve-ZaeREoVcpkgRoot {
    param(
        [string]$ExplicitValue = "",
        [object]$Configuration,
        [Parameter(Mandatory = $true)][string]$WorkspacePath
    )

    $resolved = Resolve-ZaeREoPath `
        -ExplicitValue $ExplicitValue `
        -EnvironmentNames @("VCPKG_ROOT") `
        -Configuration $Configuration `
        -ConfigurationNames @("vcpkgRoot") `
        -WorkspacePath $WorkspacePath `
        -Discovery {
            $command = Get-Command vcpkg -ErrorAction SilentlyContinue
            if ($command) { Split-Path -Parent $command.Source } else { "" }
        } `
        -Description "vcpkg root"
    if (-not $resolved -or -not (Test-Path -LiteralPath (Join-Path $resolved "vcpkg.exe") -PathType Leaf)) {
        throw "vcpkg was not found. Pass -VcpkgRoot, set VCPKG_ROOT, or configure vcpkgRoot with a checkout containing vcpkg.exe."
    }
    return $resolved
}

function Test-ZaeREoPathWithin {
    param(
        [Parameter(Mandatory = $true)][string]$Parent,
        [Parameter(Mandatory = $true)][string]$Candidate
    )

    $parentPath = (Get-ZaeREoFullPath $Parent).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $candidatePath = (Get-ZaeREoFullPath $Candidate).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    return $candidatePath.StartsWith(
        $parentPath + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase
    )
}

function Test-ZaeREoProgramRoot {
    param([Parameter(Mandatory = $true)][string]$Path)

    foreach ($environmentName in @("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432")) {
        $root = [Environment]::GetEnvironmentVariable($environmentName)
        if ($root -and ((Get-ZaeREoFullPath $Path) -eq (Get-ZaeREoFullPath $root) -or
            (Test-ZaeREoPathWithin $root $Path))) {
            return $true
        }
    }
    return $false
}

function Resolve-ZaeREoInstallRoots {
    param(
        [Parameter(Mandatory = $true)][string]$WorkspacePath,
        [object]$Configuration,
        [string]$EngineRoot = "",
        [string]$UserRoot = "",
        [string]$GameRoot = "",
        [switch]$IntoGameDir
    )

    if ($GameRoot.Trim() -and $UserRoot.Trim()) {
        throw "-GameRoot is an explicit portable/developer override and cannot be combined with -UserRoot."
    }
    if ($IntoGameDir -and ($GameRoot.Trim() -or $UserRoot.Trim())) {
        throw "-IntoGameDir installs into the resolved engine/game root and cannot be combined with -GameRoot or -UserRoot."
    }

    $portableOverride = [bool]$GameRoot.Trim()
    if ($portableOverride) {
        $userRootPath = Get-ZaeREoFullPath $GameRoot $WorkspacePath
        if (-not (Test-Path -LiteralPath $userRootPath -PathType Container) -or
            -not (Test-Path -LiteralPath (Join-Path $userRootPath "baseq2") -PathType Container)) {
            throw "Explicit -GameRoot must be a disposable/portable Rerelease directory containing baseq2: $userRootPath"
        }
        $enginePath = if ($EngineRoot.Trim()) {
            Get-ZaeREoFullPath $EngineRoot $WorkspacePath
        }
        else {
            $userRootPath
        }
        Write-Warning "Using explicit -GameRoot portable/developer override; the supported default is the per-user Saved Games root."
    }
    else {
        $enginePath = Resolve-ZaeREoPath `
            -ExplicitValue $EngineRoot `
            -EnvironmentNames @("Q2RERELEASE_ENGINE_ROOT") `
            -LegacyEnvironmentNames @("Q2RERELEASE_ROOT") `
            -Configuration $Configuration `
            -ConfigurationNames @("q2RereleaseEngineRoot") `
            -LegacyConfigurationNames @("q2RereleaseRoot") `
            -WorkspacePath $WorkspacePath `
            -Discovery { Find-ZaeREoRereleaseRoot } `
            -Description "read-only Quake II Rerelease engine/data root"
        if ($IntoGameDir) {
            # Explicit opt-in: install beside baseq2 in the resolved Rerelease
            # game directory (e.g. a Steam install) instead of the per-user root.
            # This intentionally writes under the game root, so bypass the
            # program-root guard below the same way an explicit -GameRoot does.
            $userRootPath = $enginePath
            $portableOverride = $true
            Write-Warning "Installing into the resolved Rerelease game directory (beside baseq2); this writes under the game root."
        }
        else {
            $userRootPath = Resolve-ZaeREoPath `
                -ExplicitValue $UserRoot `
                -EnvironmentNames @("Q2RERELEASE_USER_ROOT") `
                -Configuration $Configuration `
                -ConfigurationNames @("q2RereleaseUserRoot") `
                -WorkspacePath $WorkspacePath `
                -Discovery { Get-ZaeREoDefaultUserRoot } `
                -Description "writable Quake II Rerelease user-data root"
        }
    }

    if (-not $enginePath -or -not (Test-Path -LiteralPath $enginePath -PathType Container) -or
        -not (Test-Path -LiteralPath (Join-Path $enginePath "baseq2") -PathType Container)) {
        throw "The read-only engine/data root must be a Rerelease directory containing baseq2. Pass -EngineRoot or set Q2RERELEASE_ENGINE_ROOT."
    }
    if (-not $userRootPath) {
        throw "The writable user-data root could not be resolved. Pass -UserRoot or set Q2RERELEASE_USER_ROOT."
    }
    if ((Split-Path -Leaf $userRootPath).Equals("baseq2", [StringComparison]::OrdinalIgnoreCase)) {
        throw "Never target baseq2 as a writable root. Pass its user-data parent instead."
    }
    if (-not $portableOverride -and
        ((Get-ZaeREoFullPath $userRootPath) -eq (Get-ZaeREoFullPath $enginePath) -or
         (Test-ZaeREoPathWithin $enginePath $userRootPath) -or
         (Test-ZaeREoProgramRoot $userRootPath))) {
        throw "The supported writable destination cannot be the read-only engine/program root. Use the per-user default or an explicit disposable -GameRoot override."
    }

    return [pscustomobject]@{
        EngineRoot = Get-ZaeREoFullPath $enginePath
        UserRoot = Get-ZaeREoFullPath $userRootPath
        TargetPath = Get-ZaeREoFullPath (Join-Path $userRootPath "zaereo")
        PortableOverride = $portableOverride
    }
}
