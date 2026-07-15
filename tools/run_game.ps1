[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Low")]
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$EngineRoot = "",
    [string]$UserRoot = "",
    [string]$Executable = "",
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_][A-Za-z0-9_.-]*$')]
    [string]$Map,
    [switch]$Deathmatch,
    [ValidateRange(0, 3)]
    [int]$ZdmFlags = 0,
    [switch]$ProbeDeathmatchItems,
    [ValidateRange(1, 3600)]
    [int]$TimeoutSeconds = 60,
    [ValidateRange(1, 10000)]
    [int]$WaitFrames = 200,
    [string]$ReportOutput = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "zaereo_paths.ps1")

if (-not ("ZaeREoWindowProbe" -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading;

public static class ZaeREoWindowProbe
{
    private const int GWL_STYLE = -16;
    private const long WS_CAPTION = 0x00C00000L;
    private const long WS_POPUP = 0x80000000L;
    private const uint WM_KEYDOWN = 0x0100;
    private const uint WM_KEYUP = 0x0101;
    private const uint WM_CHAR = 0x0102;
    private const uint VK_OEM_3 = 0xC0;
    private const uint VK_RETURN = 0x0D;

    public sealed class WindowInfo
    {
        public IntPtr Handle;
        public long Style;
        public int[] Bounds;
    }

    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")]
    private static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool PostMessage(IntPtr hWnd, uint message, IntPtr wParam, IntPtr lParam);

    public static long GetStyle(IntPtr hWnd)
    {
        return GetWindowLongPtr(hWnd, GWL_STYLE).ToInt64();
    }

    public static bool IsWindowed(long style)
    {
        return (style & WS_CAPTION) == WS_CAPTION && (style & WS_POPUP) == 0;
    }

    public static bool HasCaption(long style)
    {
        return (style & WS_CAPTION) == WS_CAPTION;
    }

    public static bool IsPopup(long style)
    {
        return (style & WS_POPUP) != 0;
    }

    public static int[] GetBounds(IntPtr hWnd)
    {
        RECT rect;
        if (!GetWindowRect(hWnd, out rect))
            return null;
        return new[] { rect.Left, rect.Top, rect.Right - rect.Left, rect.Bottom - rect.Top };
    }

    public static WindowInfo[] GetVisibleTopLevelWindows(int processId)
    {
        var windows = new List<WindowInfo>();
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
        {
            uint ownerProcessId;
            GetWindowThreadProcessId(hWnd, out ownerProcessId);
            if (ownerProcessId != (uint)processId || !IsWindowVisible(hWnd))
                return true;
            int[] bounds = GetBounds(hWnd);
            if (bounds == null || bounds[2] <= 0 || bounds[3] <= 0)
                return true;
            windows.Add(new WindowInfo { Handle = hWnd, Style = GetStyle(hWnd), Bounds = bounds });
            return true;
        }, IntPtr.Zero);
        return windows.ToArray();
    }

    public static bool SendConsoleCommand(IntPtr hWnd, string command)
    {
        if (hWnd == IntPtr.Zero || String.IsNullOrEmpty(command) || !IsWindowVisible(hWnd))
            return false;
        BringWindowToTop(hWnd);
        SetForegroundWindow(hWnd);
        Thread.Sleep(100);
        if (!PostMessage(hWnd, WM_KEYDOWN, (IntPtr)VK_OEM_3, IntPtr.Zero) ||
            !PostMessage(hWnd, WM_KEYUP, (IntPtr)VK_OEM_3, IntPtr.Zero))
            return false;
        foreach (char character in command)
        {
            if (!PostMessage(hWnd, WM_CHAR, (IntPtr)character, IntPtr.Zero))
                return false;
        }
        return PostMessage(hWnd, WM_KEYDOWN, (IntPtr)VK_RETURN, IntPtr.Zero) &&
            PostMessage(hWnd, WM_KEYUP, (IntPtr)VK_RETURN, IntPtr.Zero);
    }
}
'@
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-StrictChildPath {
    param(
        [Parameter(Mandatory = $true)][string]$Parent,
        [Parameter(Mandatory = $true)][string]$Child,
        [string]$Description = "path"
    )
    $parentPath = (Get-ZaeREoFullPath $Parent).TrimEnd("\", "/")
    $childPath = Get-ZaeREoFullPath $Child
    if (-not $childPath.StartsWith(
        $parentPath + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "$Description must remain below '$parentPath': $childPath"
    }
    return $childPath
}

function Resolve-RereleaseExecutable {
    param([string]$EnginePath, [string]$ExplicitExecutable)

    if ($ExplicitExecutable.Trim()) {
        $candidate = Get-ZaeREoFullPath $ExplicitExecutable $EnginePath
        [void](Assert-StrictChildPath $EnginePath $candidate "Rerelease executable")
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw "Rerelease executable does not exist: $candidate"
        }
        return $candidate
    }
    foreach ($name in @("quake2ex_steam.exe", "quake2ex_gog.exe", "quake2ex.exe")) {
        $candidate = Join-Path $EnginePath $name
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            Write-Host "Rerelease executable safely discovered: $candidate"
            return $candidate
        }
    }
    throw "No supported Rerelease executable was found below $EnginePath; pass -Executable."
}

function Get-RereleaseProcesses {
    param([Parameter(Mandatory = $true)][string]$ExecutablePath)

    $expectedPath = Get-ZaeREoFullPath $ExecutablePath
    $processName = [IO.Path]::GetFileNameWithoutExtension($expectedPath)
    return @(
        Get-Process -Name $processName -ErrorAction SilentlyContinue | Where-Object {
            try {
                $_.Path -and (Get-ZaeREoFullPath $_.Path).Equals(
                    $expectedPath,
                    [StringComparison]::OrdinalIgnoreCase
                )
            }
            catch {
                $false
            }
        }
    )
}

function Write-NormalizedJson {
    param([string]$Path, [object]$Value)
    $json = ($Value | ConvertTo-Json -Depth 8) + "`n"
    [IO.File]::WriteAllText($Path, $json.Replace("`r`n", "`n"), [Text.UTF8Encoding]::new($false))
}

$workspacePath = Get-ZaeREoFullPath $WorkspaceRoot
if (-not $Deathmatch -and $ZdmFlags -ne 0) {
    throw "-ZdmFlags requires -Deathmatch."
}
if (-not $Deathmatch -and $ProbeDeathmatchItems) {
    throw "-ProbeDeathmatchItems requires -Deathmatch."
}
$configuration = Get-ZaeREoLocalConfiguration $workspacePath
$roots = Resolve-ZaeREoInstallRoots `
    -WorkspacePath $workspacePath `
    -Configuration $configuration `
    -EngineRoot $EngineRoot `
    -UserRoot $UserRoot
$enginePath = $roots.EngineRoot
$userPath = $roots.UserRoot
$modPath = $roots.TargetPath
$executablePath = Resolve-RereleaseExecutable $enginePath $Executable

$dllPath = Join-Path $modPath "game_x64.dll"
$pakPath = Join-Path $modPath "pak0.pak"
foreach ($required in @($dllPath, $pakPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Installed developer runtime input is missing: $required. Run install_dev.ps1 first."
    }
}
$managedManifest = Join-Path $modPath ".zaereo-managed-files.json"
if (-not (Test-Path -LiteralPath $managedManifest -PathType Leaf)) {
    throw "Installed mod is not a ZaeREo-managed developer stage: $modPath"
}

$stdoutPath = Join-Path $userPath "stdout.txt"
$stderrPath = Join-Path $userPath "stderr.txt"
$previousStderrWrite = if (Test-Path -LiteralPath $stderrPath -PathType Leaf) {
    (Get-Item -LiteralPath $stderrPath).LastWriteTimeUtc
}
else {
    [DateTime]::MinValue
}

if (-not $ReportOutput.Trim()) {
    $safeMap = $Map.ToLowerInvariant()
    $ReportOutput = Join-Path $workspacePath ".install\runtime-reports\$safeMap.json"
}
$reportPath = Get-ZaeREoFullPath $ReportOutput $workspacePath
$installRoot = Join-Path $workspacePath ".install"
[void](Assert-StrictChildPath $installRoot $reportPath "runtime report")

$runId = [Guid]::NewGuid().ToString("N")
$beginMarker = "ZAEREO_RUNTIME_BEGIN_$runId"
$endMarker = "ZAEREO_RUNTIME_END_$runId"
# The first process command line must not select the mod or map. The native
# window is made and checked first; only then does the wrapper deliver this
# console command to the verified, exact-PID window.
$runtimeCommands = @(
    "set v_windowmode 0",
    "set deathmatch $(if ($Deathmatch) { '1' } else { '0' })",
    "set coop 0",
    "set zdmflags $ZdmFlags",
    "set game zaereo",
    "map $Map",
    "wait $WaitFrames"
)
if ($ProbeDeathmatchItems) {
    $runtimeCommands += "sv zaereo_dm_probe"
}
$runtimeCommands += @("echo $endMarker", "quit")
$runtimeCommand = $runtimeCommands -join "; "
$arguments = @(
    "-window",
    "-width", "1280",
    "-height", "720",
    "+set", "v_windowmode", "0",
    "+set", "v_width", "1280",
    "+set", "v_height", "720",
    "+set", "com_skipIntroVideos", "1",
    "+set", "developer", "1",
    "+set", "logfile", "2",
    "+echo", $beginMarker
)

Write-Host "Runtime smoke plan"
Write-Host "  engine:  $executablePath"
Write-Host "  mod:     $modPath"
Write-Host "  map:     $Map"
Write-Host "  mode:    $(if ($Deathmatch) { 'deathmatch' } else { 'single-player' })"
Write-Host "  zdmflags: $ZdmFlags"
Write-Host "  DM item probe: $([bool]$ProbeDeathmatchItems)"
Write-Host "  report:  $reportPath"
Write-Host "  protocol: verify a visible native window before injecting the mod/map command"
if (-not $PSCmdlet.ShouldProcess($executablePath, "Launch visible windowed bootstrap, then verified ZaeREo runtime smoke for map $Map")) {
    return
}

$preexistingProcesses = @(Get-RereleaseProcesses $executablePath)
if ($preexistingProcesses.Count) {
    $ids = ($preexistingProcesses.Id | Sort-Object) -join ", "
    throw "Refusing to launch while the selected Rerelease executable is already running (PID $ids)."
}
# A just-exited Steam/KEX process can leave launch handoff state briefly alive.
# Require a continuous quiet interval so a new invocation receives its own
# startup arguments, including the authoritative pre-video -window switch.
$quiescenceDeadline = [DateTime]::UtcNow.AddSeconds(3)
while ([DateTime]::UtcNow -lt $quiescenceDeadline) {
    Start-Sleep -Milliseconds 100
    $lateProcesses = @(Get-RereleaseProcesses $executablePath)
    if ($lateProcesses.Count) {
        $ids = ($lateProcesses.Id | Sort-Object) -join ", "
        throw "Refusing to launch because the selected Rerelease executable appeared during the 3-second startup quiescence interval (PID $ids)."
    }
}

$started = [DateTime]::UtcNow
$process = Start-Process `
    -FilePath $executablePath `
    -ArgumentList $arguments `
    -WorkingDirectory $enginePath `
    -PassThru
$observedProcesses = @{}
$observedProcesses[$process.Id] = $process
$deadline = $started.AddSeconds($TimeoutSeconds)
$log = ""
$sessionComplete = $false
$activeProcesses = @($process)
$windowProbe = $null
$windowedVisibleObserved = $false
$nonWindowedVisibleObserved = $false
$windowSafetyAborted = $false
$modMapCommandInjected = $false
$modMapCommandInjectionFailed = $false
do {
    $verifiedWindowHandles = @()
    foreach ($candidate in @(Get-RereleaseProcesses $executablePath)) {
        if ($candidate.StartTime.ToUniversalTime() -ge $started.AddSeconds(-2)) {
            $observedProcesses[$candidate.Id] = $candidate
            $candidate.Refresh()
            foreach ($window in @([ZaeREoWindowProbe]::GetVisibleTopLevelWindows($candidate.Id))) {
                if ($null -ne $window) {
                    $style = $window.Style
                    $bounds = $window.Bounds
                    $isWindowed = [ZaeREoWindowProbe]::IsWindowed($style)
                    $windowedVisibleObserved = $windowedVisibleObserved -or $isWindowed
                    $nonWindowedVisibleObserved = $nonWindowedVisibleObserved -or -not $isWindowed
                    $windowProbe = [ordered]@{
                        method = "win32-visible-top-level-window-enumeration"
                        process_id = $candidate.Id
                        style_hex = "0x$($style.ToString('X8'))"
                        captioned = [ZaeREoWindowProbe]::HasCaption($style)
                        popup = [ZaeREoWindowProbe]::IsPopup($style)
                        left = $bounds[0]
                        top = $bounds[1]
                        width = $bounds[2]
                        height = $bounds[3]
                    }
                    if (-not $isWindowed) {
                        $windowSafetyAborted = $true
                        try {
                            $current = Get-Process -Id $candidate.Id -ErrorAction Stop
                            if ($current.StartTime.ToUniversalTime() -ge $started.AddSeconds(-2) -and
                                $current.Path -and (Get-ZaeREoFullPath $current.Path).Equals(
                                    $executablePath,
                                    [StringComparison]::OrdinalIgnoreCase
                                )) {
                                Stop-Process -Id $current.Id -Force
                                $current.WaitForExit()
                            }
                        }
                        catch {
                            # The exact observed process may already have exited.
                        }
                    }
                    else {
                        $verifiedWindowHandles += [IntPtr]$window.Handle
                    }
                }
            }
        }
    }
    if (-not $windowSafetyAborted -and -not $modMapCommandInjected -and $verifiedWindowHandles.Count) {
        $modMapCommandInjected = [ZaeREoWindowProbe]::SendConsoleCommand(
            $verifiedWindowHandles[0],
            $runtimeCommand
        )
        if (-not $modMapCommandInjected) {
            $modMapCommandInjectionFailed = $true
            $windowSafetyAborted = $true
        }
    }
    if (Test-Path -LiteralPath $stdoutPath -PathType Leaf) {
        $currentLog = Get-Content -LiteralPath $stdoutPath -Raw
        $log = if ($null -eq $currentLog) { "" } else { [string]$currentLog }
        $currentBeginIndex = $log.LastIndexOf($beginMarker, [StringComparison]::Ordinal)
        $currentSessionText = if ($currentBeginIndex -ge 0) {
            $log.Substring($currentBeginIndex)
        }
        else {
            ""
        }
        $sessionComplete = $currentSessionText.Contains($endMarker) -and
            $currentSessionText.Contains("==== ShutdownGame ====")
    }
    $activeProcesses = @(
        foreach ($candidate in $observedProcesses.Values) {
            try {
                $candidate.Refresh()
                if (-not $candidate.HasExited) { $candidate }
            }
            catch {
                # A process that disappeared between enumeration and refresh is exited.
            }
        }
    )
    if ($sessionComplete -and $activeProcesses.Count -eq 0) {
        break
    }
    if ($windowSafetyAborted) {
        break
    }
    Start-Sleep -Milliseconds 100
} while ([DateTime]::UtcNow -lt $deadline)
$timedOut = -not $windowSafetyAborted -and
    -not ($sessionComplete -and $activeProcesses.Count -eq 0)
if ($windowSafetyAborted -or $timedOut) {
    foreach ($candidate in $activeProcesses) {
        try {
            $current = Get-Process -Id $candidate.Id -ErrorAction Stop
            if ($current.StartTime.ToUniversalTime() -ge $started.AddSeconds(-2) -and
                $current.Path -and (Get-ZaeREoFullPath $current.Path).Equals(
                    $executablePath,
                    [StringComparison]::OrdinalIgnoreCase
                )) {
                Stop-Process -Id $current.Id -Force
                $current.WaitForExit()
            }
        }
        catch {
            # The exact observed process may already have exited.
        }
    }
}
$finished = [DateTime]::UtcNow

try {
    if (-not $process.HasExited) { $process.WaitForExit() }
    $processExitCode = $process.ExitCode
}
catch {
    $processExitCode = -1
}

if (-not $log -and -not $windowSafetyAborted) {
    throw "Rerelease did not produce its stdout log: $stdoutPath"
}
$beginIndex = $log.LastIndexOf($beginMarker, [StringComparison]::Ordinal)
$endIndex = if ($beginIndex -ge 0) {
    $log.IndexOf($endMarker, $beginIndex + $beginMarker.Length, [StringComparison]::Ordinal)
}
else {
    -1
}
$sessionBracketed = $beginIndex -ge 0 -and $endIndex -gt $beginIndex
$sessionLog = if ($sessionBracketed) {
    $log.Substring($beginIndex)
}
else {
    ""
}
$stderrText = if ((Test-Path -LiteralPath $stderrPath -PathType Leaf) -and
    (Get-Item -LiteralPath $stderrPath).LastWriteTimeUtc -gt $previousStderrWrite) {
    $currentStderr = Get-Content -LiteralPath $stderrPath -Raw
    if ($null -eq $currentStderr) { "" } else { [string]$currentStderr }
}
else {
    ""
}

$markers = [ordered]@{
    session_begin = $beginIndex -ge 0
    windowed_mode_confirmed = $windowedVisibleObserved -and -not $nonWindowedVisibleObserved
    mod_map_command_injected_after_window_verification = $modMapCommandInjected
    game_dll_loaded = [bool]($sessionLog -match '(?im)^LoadLibrary \(.+[\\/]zaereo[\\/]game_x64\.dll\)\s*$')
    game_initialized = $sessionLog.Contains("==== InitGame ====")
    map_spawned = [bool]($sessionLog -match ("(?im)^SpawnServer:\s*" + [regex]::Escape($Map) + "\s*$"))
    client_entered = [bool]($sessionLog -match '(?im)^(?:.+ entered the game|Begin\(\) from .+)\s*$')
    game_shutdown = $sessionLog.Contains("==== ShutdownGame ====")
    session_end = $endIndex -gt $beginIndex
}
$fatalPatterns = @(
    '(?im)^LoadLibrary failed',
    '(?im)^ERROR:\s',
    '(?im)Could not load game library',
    '(?im)Entry point .* not found'
)
$fatalMatches = @()
foreach ($pattern in $fatalPatterns) {
    $match = [regex]::Match($sessionLog, $pattern)
    if ($match.Success) { $fatalMatches += $match.Value }
}
$acceptedExitCode = $processExitCode -in @(0, 1)
$zaeroEntitiesAddedMatches = [regex]::Matches(
    $sessionLog,
    '(?im)^([0-8]) Zaero entities added\s*$'
)
$zaeroEntitiesAdded = if ($zaeroEntitiesAddedMatches.Count) {
    [int]$zaeroEntitiesAddedMatches[$zaeroEntitiesAddedMatches.Count - 1].Groups[1].Value
}
else {
    $null
}
$probeBeginMatches = [regex]::Matches(
    $sessionLog,
    '(?im)^ZAEREO_DM_PROBE_BEGIN recorded=([0-8])\s*$'
)
$probeItemMatches = [regex]::Matches(
    $sessionLog,
    '(?im)^ZAEREO_DM_PROBE_ITEM index=([0-7]) classname=([a-z0-9_]+) spawn=([1-9][0-9]*) attempt=([1-4]) entity=([1-9][0-9]*) start=(-?[0-9]+\.[0-9]{3}),(-?[0-9]+\.[0-9]{3}),(-?[0-9]+\.[0-9]{3}) placed=(-?[0-9]+\.[0-9]{3}),(-?[0-9]+\.[0-9]{3}),(-?[0-9]+\.[0-9]{3}) live=([01]) origin=(-?[0-9]+\.[0-9]{3}),(-?[0-9]+\.[0-9]{3}),(-?[0-9]+\.[0-9]{3}) toss=([01]) trigger=([01]) touch=([01]) ir=([01]) grounded=([01])\s*$'
)
$probeEndMatches = [regex]::Matches(
    $sessionLog,
    '(?im)^ZAEREO_DM_PROBE_END recorded=([0-8]) live=([0-8])\s*$'
)
$probeItems = @()
foreach ($match in $probeItemMatches) {
    $startOrigin = @(
        [double]::Parse($match.Groups[6].Value, [Globalization.CultureInfo]::InvariantCulture),
        [double]::Parse($match.Groups[7].Value, [Globalization.CultureInfo]::InvariantCulture),
        [double]::Parse($match.Groups[8].Value, [Globalization.CultureInfo]::InvariantCulture)
    )
    $placedOrigin = @(
        [double]::Parse($match.Groups[9].Value, [Globalization.CultureInfo]::InvariantCulture),
        [double]::Parse($match.Groups[10].Value, [Globalization.CultureInfo]::InvariantCulture),
        [double]::Parse($match.Groups[11].Value, [Globalization.CultureInfo]::InvariantCulture)
    )
    $liveOrigin = @(
        [double]::Parse($match.Groups[13].Value, [Globalization.CultureInfo]::InvariantCulture),
        [double]::Parse($match.Groups[14].Value, [Globalization.CultureInfo]::InvariantCulture),
        [double]::Parse($match.Groups[15].Value, [Globalization.CultureInfo]::InvariantCulture)
    )
    $deltaX = $placedOrigin[0] - $startOrigin[0]
    $deltaY = $placedOrigin[1] - $startOrigin[1]
    $probeItems += [ordered]@{
        set_index = [int]$match.Groups[1].Value
        classname = $match.Groups[2].Value
        spawn_ordinal = [int]$match.Groups[3].Value
        attempt = [int]$match.Groups[4].Value
        entity_number = [int]$match.Groups[5].Value
        start_origin = $startOrigin
        placed_origin = $placedOrigin
        live_origin = $liveOrigin
        placement_radius_xy = [Math]::Sqrt(($deltaX * $deltaX) + ($deltaY * $deltaY))
        placement_height = $placedOrigin[2] - $startOrigin[2]
        live = $match.Groups[12].Value -eq "1"
        movetype_toss = $match.Groups[16].Value -eq "1"
        solid_trigger = $match.Groups[17].Value -eq "1"
        touch_item = $match.Groups[18].Value -eq "1"
        ir_visible = $match.Groups[19].Value -eq "1"
        grounded = $match.Groups[20].Value -eq "1"
    }
}
$expectedProbeClassnames = @(
    "weapon_soniccannon",
    "weapon_sniperrifle",
    "weapon_flaregun",
    "ammo_ired",
    "ammo_a2k",
    "ammo_flares",
    "ammo_empnuke",
    "ammo_plasmashield"
)
$probeOrderValid = $true
foreach ($item in $probeItems) {
    if ($item.set_index -ge $expectedProbeClassnames.Count -or
        $item.classname -cne $expectedProbeClassnames[$item.set_index]) {
        $probeOrderValid = $false
        break
    }
}
$probeBeginCount = if ($probeBeginMatches.Count -eq 1) {
    [int]$probeBeginMatches[0].Groups[1].Value
}
else { $null }
$probeEndRecorded = if ($probeEndMatches.Count -eq 1) {
    [int]$probeEndMatches[0].Groups[1].Value
}
else { $null }
$probeEndLive = if ($probeEndMatches.Count -eq 1) {
    [int]$probeEndMatches[0].Groups[2].Value
}
else { $null }
$probeInvalidItems = @($probeItems | Where-Object {
    -not $_.live -or -not $_.movetype_toss -or -not $_.solid_trigger -or
    -not $_.touch_item -or -not $_.ir_visible -or
    $_.placement_radius_xy -lt 127.99 -or $_.placement_radius_xy -gt 128.01 -or
    $_.placement_height -lt 15.99 -or $_.placement_height -gt 16.01
})
$probeComplete = -not $ProbeDeathmatchItems -or (
    $probeBeginMatches.Count -eq 1 -and
    $probeEndMatches.Count -eq 1 -and
    $probeBeginCount -eq $probeItems.Count -and
    $probeEndRecorded -eq $probeItems.Count -and
    $probeEndLive -eq $probeItems.Count -and
    $probeInvalidItems.Count -eq 0 -and
    $probeOrderValid -and
    ($null -eq $zaeroEntitiesAdded -or
        $zaeroEntitiesAdded -eq $probeItems.Count)
)
$probeReport = if ($ProbeDeathmatchItems) {
    [ordered]@{
        requested = $true
        complete = $probeComplete
        recorded_count = $probeEndRecorded
        live_count = $probeEndLive
        items = $probeItems
    }
}
else { $null }
$crashDumps = @(
    Get-ChildItem -LiteralPath $userPath -Filter "*.dmp" -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTimeUtc -ge $started.AddSeconds(-2) } |
        ForEach-Object { [IO.Path]::GetRelativePath($userPath, $_.FullName).Replace("\", "/") }
)
$passed = -not $windowSafetyAborted -and
    -not $modMapCommandInjectionFailed -and
    -not $timedOut -and
    $sessionBracketed -and
    $acceptedExitCode -and
    $crashDumps.Count -eq 0 -and
    -not $stderrText.Trim() -and
    @($markers.Values | Where-Object { -not $_ }).Count -eq 0 -and
    $fatalMatches.Count -eq 0 -and
    $probeComplete

$report = [ordered]@{
    schema = "zaereo.runtime-smoke/v2"
    schema_version = 2
    result = if ($passed) { "passed" } else { "failed" }
    run_id = $runId
    started_utc = $started.ToString("yyyy-MM-ddTHH:mm:ssZ")
    finished_utc = $finished.ToString("yyyy-MM-ddTHH:mm:ssZ")
    map = $Map
    game_mode = if ($Deathmatch) { "deathmatch" } else { "single-player" }
    zdmflags = $ZdmFlags
    zaero_entities_added = $zaeroEntitiesAdded
    dm_item_probe = $probeReport
    game_directory = "zaereo"
    window_mode = "windowed"
    window_width = 1280
    window_height = 720
    window_probe = $windowProbe
    non_windowed_visible_observed = $nonWindowedVisibleObserved
    window_safety_abort = $windowSafetyAborted
    launch_protocol = "two-stage-window-before-mod-map/v1"
    mod_map_command_injected_after_window_verification = $modMapCommandInjected
    engine_executable = Split-Path -Leaf $executablePath
    engine_sha256 = Get-Sha256 $executablePath
    game_dll_sha256 = Get-Sha256 $dllPath
    pak0_sha256 = Get-Sha256 $pakPath
    managed_manifest_sha256 = Get-Sha256 $managedManifest
    process_exit_code = $processExitCode
    process_exit_code_accepted = $acceptedExitCode
    timed_out = $timedOut
    wait_frames = $WaitFrames
    markers = $markers
    stderr_empty = -not [bool]$stderrText.Trim()
    fatal_matches = $fatalMatches
    crash_dumps = $crashDumps
    console_log = "stdout.txt"
    publication_status = "private-local-only"
}
New-Item -ItemType Directory -Path (Split-Path -Parent $reportPath) -Force | Out-Null
Write-NormalizedJson $reportPath $report

if (-not $passed) {
    throw "Runtime smoke failed; private report: $reportPath"
}
Write-Host "Runtime smoke passed: map=$Map exit=$processExitCode report=$reportPath"
