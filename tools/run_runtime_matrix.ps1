[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Low")]
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$ScenarioFile = (Join-Path $PSScriptRoot "runtime-scenarios.json"),
    [string]$RunnerPath = (Join-Path $PSScriptRoot "run_game.ps1"),
    [string]$EngineRoot = "",
    [string]$UserRoot = "",
    [string]$Executable = "",
    [string]$ResultRoot = "build/test-results",
    [string]$RunId = "",
    [switch]$ManualCommandDelivery
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "zaereo_paths.ps1")

function Assert-StrictChildPath {
    param(
        [Parameter(Mandatory = $true)][string]$Parent,
        [Parameter(Mandatory = $true)][string]$Child,
        [Parameter(Mandatory = $true)][string]$Description
    )

    if (-not (Test-ZaeREoPathWithin $Parent $Child)) {
        throw "$Description must remain below '$Parent': $Child"
    }
    return Get-ZaeREoFullPath $Child
}

function Assert-ExactProperties {
    param(
        [Parameter(Mandatory = $true)][object]$Value,
        [Parameter(Mandatory = $true)][string[]]$Names,
        [Parameter(Mandatory = $true)][string]$Description
    )

    $actual = @($Value.PSObject.Properties.Name | Sort-Object)
    $expected = @($Names | Sort-Object)
    if (($actual -join "`n") -ne ($expected -join "`n")) {
        throw "$Description has unsupported, missing, or duplicate properties. Expected: $($expected -join ', '); actual: $($actual -join ', ')."
    }
}

function Assert-IntegerInRange {
    param(
        [Parameter(Mandatory = $true)][object]$Value,
        [Parameter(Mandatory = $true)][int]$Minimum,
        [Parameter(Mandatory = $true)][int]$Maximum,
        [Parameter(Mandatory = $true)][string]$Description
    )

    if ($Value -isnot [byte] -and $Value -isnot [int16] -and
        $Value -isnot [int32] -and $Value -isnot [int64]) {
        throw "$Description must be an integer."
    }
    $number = [int64]$Value
    if ($number -lt $Minimum -or $number -gt $Maximum) {
        throw "$Description must be in [$Minimum, $Maximum], got $number."
    }
    return [int]$number
}

function Write-NormalizedJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Value
    )

    $json = ($Value | ConvertTo-Json -Depth 8) + "`n"
    [IO.File]::WriteAllText($Path, $json.Replace("`r`n", "`n"), [Text.UTF8Encoding]::new($false))
}

function Escape-Xml {
    param([string]$Value)
    return [Security.SecurityElement]::Escape($Value)
}

function Get-ReportProperty {
    param(
        [Parameter(Mandatory = $true)][object]$Report,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][Collections.Generic.List[string]]$Failures
    )

    $property = $Report.PSObject.Properties[$Name]
    if ($null -eq $property) {
        [void]$Failures.Add("missing '$Name'")
        return $null
    }
    # Empty JSON arrays are evidence. Preserve them as one value rather than
    # letting PowerShell enumerate them into an indistinguishable null result.
    return ,$property.Value
}

function Test-PassedRuntimeSmokeReport {
    param(
        [Parameter(Mandatory = $true)][object]$Report,
        [Parameter(Mandatory = $true)][object]$Scenario
    )

    $failures = [Collections.Generic.List[string]]::new()
    $map = Get-ReportProperty $Report "map" $failures
    $gameMode = Get-ReportProperty $Report "game_mode" $failures
    $zdmFlags = Get-ReportProperty $Report "zdmflags" $failures
    $windowMode = Get-ReportProperty $Report "window_mode" $failures
    $windowProbe = Get-ReportProperty $Report "window_probe" $failures
    $focusDiagnostic = Get-ReportProperty $Report "focus_diagnostic" $failures
    $nonWindowedVisible = Get-ReportProperty $Report "non_windowed_visible_observed" $failures
    $windowSafetyAbort = Get-ReportProperty $Report "window_safety_abort" $failures
    $launchProtocol = Get-ReportProperty $Report "launch_protocol" $failures
    $commandDelivery = Get-ReportProperty $Report "command_delivery" $failures
    $commandInjected = Get-ReportProperty $Report "mod_map_command_injected_after_window_verification" $failures
    $exitAccepted = Get-ReportProperty $Report "process_exit_code_accepted" $failures
    $timedOut = Get-ReportProperty $Report "timed_out" $failures
    $markers = Get-ReportProperty $Report "markers" $failures
    $stderrEmpty = Get-ReportProperty $Report "stderr_empty" $failures
    $fatalMatches = Get-ReportProperty $Report "fatal_matches" $failures
    $crashDumps = Get-ReportProperty $Report "crash_dumps" $failures
    $residualProcessIds = Get-ReportProperty $Report "residual_process_ids" $failures
    $publicationStatus = Get-ReportProperty $Report "publication_status" $failures

    if ($map -ne [string]$Scenario.map) { [void]$failures.Add("map does not match scenario") }
    $expectedMode = if ($Scenario.deathmatch) { "deathmatch" } else { "single-player" }
    if ($gameMode -ne $expectedMode) { [void]$failures.Add("game_mode does not match scenario") }
    if ($zdmFlags -isnot [byte] -and $zdmFlags -isnot [int16] -and $zdmFlags -isnot [int32] -and $zdmFlags -isnot [int64]) {
        [void]$failures.Add("zdmflags is not an integer")
    }
    elseif ([int]$zdmFlags -ne [int]$Scenario.zdmflags) {
        [void]$failures.Add("zdmflags does not match scenario")
    }
    if ($windowMode -ne "windowed") { [void]$failures.Add("window_mode is not windowed") }
    if ($null -eq $windowProbe) { [void]$failures.Add("window_probe is missing") }
    if ($null -eq $focusDiagnostic) { [void]$failures.Add("focus_diagnostic is missing") }
    if ($nonWindowedVisible -ne $false) { [void]$failures.Add("non-windowed visible window was observed") }
    if ($windowSafetyAbort -ne $false) { [void]$failures.Add("window safety abort was recorded") }
    if ($launchProtocol -ne "two-stage-window-before-mod-map/v1") { [void]$failures.Add("launch protocol is not current v2") }
    if ($commandDelivery -ne "engine-confirmed") { [void]$failures.Add("command delivery is not engine-confirmed") }
    if ($commandInjected -ne $true) { [void]$failures.Add("mod/map command was not recorded after window verification") }
    if ($exitAccepted -ne $true) { [void]$failures.Add("process exit code was not accepted") }
    if ($timedOut -ne $false) { [void]$failures.Add("runtime timed out") }
    if ($stderrEmpty -ne $true) { [void]$failures.Add("stderr was not empty") }
    if ($publicationStatus -ne "private-local-only") { [void]$failures.Add("report is not private-local-only") }
    if ($null -eq $fatalMatches -or @($fatalMatches).Count -ne 0) { [void]$failures.Add("fatal output was recorded") }
    if ($null -eq $crashDumps -or @($crashDumps).Count -ne 0) { [void]$failures.Add("crash dumps were recorded") }
    if ($null -eq $residualProcessIds -or @($residualProcessIds).Count -ne 0) { [void]$failures.Add("residual process IDs were recorded") }

    if ($null -eq $markers) {
        [void]$failures.Add("markers are missing")
    }
    else {
        foreach ($markerName in @(
            "session_begin", "windowed_mode_confirmed",
            "mod_map_command_injected_after_window_verification", "game_dll_loaded",
            "game_initialized", "map_spawned", "client_entered", "game_shutdown", "session_end"
        )) {
            $marker = $markers.PSObject.Properties[$markerName]
            if ($null -eq $marker -or $marker.Value -ne $true) {
                [void]$failures.Add("marker '$markerName' is not true")
            }
        }
    }
    return $failures.ToArray()
}

function Write-JUnit {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object[]]$Results,
        [Parameter(Mandatory = $true)][TimeSpan]$Duration
    )

    $failed = @($Results | Where-Object { $_.result -ne "passed" }).Count
    $builder = [Text.StringBuilder]::new()
    [void]$builder.AppendLine('<?xml version="1.0" encoding="utf-8"?>')
    [void]$builder.Append('<testsuite name="zaereo.runtime" tests="')
    [void]$builder.Append($Results.Count)
    [void]$builder.Append('" failures="')
    [void]$builder.Append($failed)
    [void]$builder.Append('" errors="0" skipped="0" time="')
    [void]$builder.Append($Duration.TotalSeconds.ToString("0.000", [Globalization.CultureInfo]::InvariantCulture))
    [void]$builder.AppendLine('">')
    foreach ($result in $Results) {
        [void]$builder.Append('  <testcase classname="zaereo.runtime" name="')
        [void]$builder.Append((Escape-Xml $result.id))
        [void]$builder.Append('" time="')
        [void]$builder.Append($result.duration_seconds.ToString("0.000", [Globalization.CultureInfo]::InvariantCulture))
        [void]$builder.AppendLine('">')
        if ($result.result -ne "passed") {
            [void]$builder.Append('    <failure message="')
            [void]$builder.Append((Escape-Xml $result.failure))
            [void]$builder.AppendLine('" />')
        }
        [void]$builder.AppendLine('  </testcase>')
    }
    [void]$builder.AppendLine('</testsuite>')
    [IO.File]::WriteAllText($Path, $builder.ToString().Replace("`r`n", "`n"), [Text.UTF8Encoding]::new($false))
}

$workspacePath = Get-ZaeREoFullPath $WorkspaceRoot
$scenarioPath = Get-ZaeREoFullPath $ScenarioFile $workspacePath
$runnerPath = Get-ZaeREoFullPath $RunnerPath $workspacePath
$buildRoot = Get-ZaeREoFullPath (Join-Path $workspacePath "build")
$resultRootPath = Get-ZaeREoFullPath $ResultRoot $workspacePath
$privateReportRoot = Get-ZaeREoFullPath (Join-Path $workspacePath ".install\runtime-matrix")
[void](Assert-StrictChildPath $workspacePath $scenarioPath "runtime scenario file")
[void](Assert-StrictChildPath $workspacePath $runnerPath "runtime runner")
[void](Assert-StrictChildPath $buildRoot $resultRootPath "runtime matrix results")
[void](Assert-StrictChildPath (Get-ZaeREoFullPath (Join-Path $workspacePath ".install")) $privateReportRoot "private runtime reports")

if (-not (Test-Path -LiteralPath $scenarioPath -PathType Leaf)) {
    throw "Runtime scenario file does not exist: $scenarioPath"
}
if (-not (Test-Path -LiteralPath $runnerPath -PathType Leaf)) {
    throw "Runtime runner does not exist: $runnerPath"
}

try {
    $matrix = Get-Content -LiteralPath $scenarioPath -Raw | ConvertFrom-Json
}
catch {
    throw "Could not parse runtime scenario file '$scenarioPath': $($_.Exception.Message)"
}
Assert-ExactProperties $matrix @("schema", "schema_version", "scenarios") "runtime matrix"
if ($matrix.schema -ne "zaereo.runtime-matrix/v1" -or $matrix.schema_version -ne 1) {
    throw "Unsupported runtime matrix schema '$($matrix.schema)' version '$($matrix.schema_version)'."
}
$scenarios = @($matrix.scenarios)
if ($scenarios.Count -eq 0) {
    throw "Runtime matrix must contain at least one scenario."
}

$scenarioIds = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($scenario in $scenarios) {
    Assert-ExactProperties $scenario @(
        "id", "map", "deathmatch", "zdmflags", "probe_deathmatch_items",
        "wait_frames", "timeout_seconds", "requires_private_content"
    ) "runtime scenario"
    if ($scenario.id -isnot [string] -or $scenario.id -notmatch '^[a-z0-9][a-z0-9_.-]*$') {
        throw ("Runtime scenario id must match {0}: '{1}'." -f '^[a-z0-9][a-z0-9_.-]*$', $scenario.id)
    }
    if (-not $scenarioIds.Add($scenario.id)) {
        throw "Duplicate runtime scenario id: $($scenario.id)"
    }
    if ($scenario.map -isnot [string] -or $scenario.map -notmatch '^[A-Za-z0-9_][A-Za-z0-9_.-]*$') {
        throw "Runtime scenario '$($scenario.id)' has an invalid map '$($scenario.map)'."
    }
    if ($scenario.deathmatch -isnot [bool] -or $scenario.probe_deathmatch_items -isnot [bool] -or
        $scenario.requires_private_content -isnot [bool] -or -not $scenario.requires_private_content) {
        throw "Runtime scenario '$($scenario.id)' has invalid boolean fields or is not marked private-content-only."
    }
    $zdmFlags = Assert-IntegerInRange $scenario.zdmflags 0 3 "Runtime scenario '$($scenario.id)' zdmflags"
    [void](Assert-IntegerInRange $scenario.wait_frames 1 10000 "Runtime scenario '$($scenario.id)' wait_frames")
    [void](Assert-IntegerInRange $scenario.timeout_seconds 1 3600 "Runtime scenario '$($scenario.id)' timeout_seconds")
    if (-not $scenario.deathmatch -and ($zdmFlags -ne 0 -or $scenario.probe_deathmatch_items)) {
        throw "Runtime scenario '$($scenario.id)' uses deathmatch-only settings outside deathmatch."
    }
}

if (-not $RunId.Trim()) {
    $RunId = [Guid]::NewGuid().ToString("N")
}
if ($RunId -notmatch '^[a-z0-9][a-z0-9_.-]*$') {
    throw ("-RunId must match {0}: '{1}'." -f '^[a-z0-9][a-z0-9_.-]*$', $RunId)
}
$resultDirectory = Join-Path $resultRootPath $RunId
$reportDirectory = Join-Path $privateReportRoot $RunId

Write-Host "Runtime matrix plan"
Write-Host "  scenarios: $($scenarios.Count)"
Write-Host "  runner:    $runnerPath"
Write-Host "  results:   $resultDirectory"
Write-Host "  reports:   $reportDirectory"
Write-Host "  delivery:  $(if ($ManualCommandDelivery) { 'manual engine-confirmed' } else { 'foreground-gated system input' })"
foreach ($scenario in $scenarios) {
    Write-Host "  case:      $($scenario.id) ($($scenario.map))"
}
if (-not $PSCmdlet.ShouldProcess($resultDirectory, "Run private always-windowed runtime matrix")) {
    return
}

New-Item -ItemType Directory -Path $resultDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
$started = [DateTime]::UtcNow
$results = [Collections.Generic.List[object]]::new()
foreach ($scenario in $scenarios) {
    $caseStarted = [DateTime]::UtcNow
    $reportPath = Join-Path $reportDirectory "$($scenario.id).json"
    $runnerArguments = @(
        "-WorkspaceRoot", $workspacePath,
        "-Map", [string]$scenario.map,
        "-ZdmFlags", [string]$scenario.zdmflags,
        "-WaitFrames", [string]$scenario.wait_frames,
        "-TimeoutSeconds", [string]$scenario.timeout_seconds,
        "-ReportOutput", $reportPath
    )
    if ($scenario.deathmatch) { $runnerArguments += "-Deathmatch" }
    if ($scenario.probe_deathmatch_items) { $runnerArguments += "-ProbeDeathmatchItems" }
    if ($ManualCommandDelivery) { $runnerArguments += "-ManualCommandDelivery" }
    if ($EngineRoot.Trim()) { $runnerArguments += @("-EngineRoot", $EngineRoot) }
    if ($UserRoot.Trim()) { $runnerArguments += @("-UserRoot", $UserRoot) }
    if ($Executable.Trim()) { $runnerArguments += @("-Executable", $Executable) }

    $runnerFailure = ""
    try {
        & $runnerPath @runnerArguments
    }
    catch {
        $runnerFailure = $_.Exception.Message
    }

    $result = "no-report"
    $failure = if ($runnerFailure) { $runnerFailure } else { "Runtime wrapper did not produce a report." }
    $commandDelivery = $null
    $launchProtocol = $null
    $focusDiagnostic = $null
    if (Test-Path -LiteralPath $reportPath -PathType Leaf) {
        try {
            $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
            if ($report.schema -ne "zaereo.runtime-smoke/v2" -or $report.schema_version -ne 2 -or
                $report.result -notin @("passed", "failed")) {
                $result = "invalid-report"
                $failure = "Runtime wrapper produced an unsupported report."
            }
            else {
                $commandProperty = $report.PSObject.Properties["command_delivery"]
                if ($null -ne $commandProperty -and $commandProperty.Value -is [string]) {
                    $commandDelivery = [string]$commandProperty.Value
                }
                $protocolProperty = $report.PSObject.Properties["launch_protocol"]
                if ($null -ne $protocolProperty -and $protocolProperty.Value -is [string]) {
                    $launchProtocol = [string]$protocolProperty.Value
                }
                $focusProperty = $report.PSObject.Properties["focus_diagnostic"]
                if ($null -ne $focusProperty) {
                    $focusDiagnostic = $focusProperty.Value
                }
                $result = [string]$report.result
                if ($result -eq "passed") {
                    $evidenceFailures = @(Test-PassedRuntimeSmokeReport $report $scenario)
                    if ($evidenceFailures.Count -ne 0) {
                        $result = "invalid-report"
                        $failure = "Runtime wrapper reported passed without required v2 evidence: $($evidenceFailures -join '; ')"
                    }
                    else {
                        $failure = ""
                    }
                }
                elseif (-not $runnerFailure) {
                    $failure = "Runtime wrapper reported failure."
                }
            }
        }
        catch {
            $result = "invalid-report"
            $failure = "Runtime wrapper report could not be parsed or validated: $($_.Exception.Message)"
        }
    }
    $duration = [DateTime]::UtcNow - $caseStarted
    $results.Add([ordered]@{
        id = [string]$scenario.id
        map = [string]$scenario.map
        result = $result
        duration_seconds = [Math]::Round($duration.TotalSeconds, 3)
        report = ".install/runtime-matrix/$RunId/$($scenario.id).json"
        launch_protocol = $launchProtocol
        command_delivery = $commandDelivery
        focus_diagnostic = $focusDiagnostic
        failure = $failure
    })
}
$finished = [DateTime]::UtcNow
$failedCount = @($results | Where-Object { $_.result -ne "passed" }).Count
$summary = [ordered]@{
    schema = "zaereo.runtime-matrix-result/v1"
    schema_version = 1
    result = if ($failedCount -eq 0) { "passed" } else { "failed" }
    run_id = $RunId
    scenario_file_sha256 = (Get-FileHash -LiteralPath $scenarioPath -Algorithm SHA256).Hash.ToLowerInvariant()
    started_utc = $started.ToString("yyyy-MM-ddTHH:mm:ssZ")
    finished_utc = $finished.ToString("yyyy-MM-ddTHH:mm:ssZ")
    total = $results.Count
    passed = $results.Count - $failedCount
    failed = $failedCount
    scenarios = @($results)
    manual_command_delivery = [bool]$ManualCommandDelivery
    publication_status = "private-local-only"
}
$jsonPath = Join-Path $resultDirectory "runtime-matrix.json"
$junitPath = Join-Path $resultDirectory "junit.xml"
Write-NormalizedJson $jsonPath $summary
Write-JUnit $junitPath @($results) ($finished - $started)

if ($failedCount -ne 0) {
    throw "Runtime matrix failed ($failedCount/$($results.Count)); private results: $resultDirectory"
}
Write-Host "Runtime matrix passed: $($results.Count) scenarios; results: $resultDirectory"
