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
    [switch]$ManualCommandDelivery,
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
    private const uint VK_OEM_3 = 0xC0;
    private const uint VK_RETURN = 0x0D;
    private const uint VK_SHIFT = 0x10;
    private const uint VK_CONTROL = 0x11;
    private const uint VK_MENU = 0x12;
    private const int SW_RESTORE = 9;
    private const uint INPUT_KEYBOARD = 1;
    private const uint KEYEVENTF_KEYUP = 0x0002;
    private const uint KEYEVENTF_SCANCODE = 0x0008;
    private const uint MAPVK_VK_TO_VSC = 0;

    public static string LastConsoleCommandStatus { get; private set; } = "not-attempted";
    public static string LastFocusStage { get; private set; } = "not-attempted";
    public static uint LastFocusForegroundProcessId { get; private set; } = 0;
    public static bool LastFocusTargetForeground { get; private set; } = false;

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

    [StructLayout(LayoutKind.Sequential)]
    private struct INPUT
    {
        public uint Type;
        public InputUnion Union;
    }

    [StructLayout(LayoutKind.Explicit)]
    private struct InputUnion
    {
        [FieldOffset(0)]
        public MOUSEINPUT Mouse;

        [FieldOffset(0)]
        public KEYBDINPUT Keyboard;

        [FieldOffset(0)]
        public HARDWAREINPUT Hardware;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct MOUSEINPUT
    {
        public int DeltaX;
        public int DeltaY;
        public uint MouseData;
        public uint Flags;
        public uint Time;
        public IntPtr ExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct KEYBDINPUT
    {
        public ushort VirtualKey;
        public ushort ScanCode;
        public uint Flags;
        public uint Time;
        public IntPtr ExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct HARDWAREINPUT
    {
        public uint Message;
        public ushort ParameterLow;
        public ushort ParameterHigh;
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

    [DllImport("kernel32.dll")]
    private static extern uint GetCurrentThreadId();

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool ShowWindow(IntPtr hWnd, int command);

    [DllImport("user32.dll")]
    private static extern IntPtr SetActiveWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern IntPtr SetFocus(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern void SwitchToThisWindow(IntPtr hWnd, [MarshalAs(UnmanagedType.Bool)] bool altTab);

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool AttachThreadInput(uint firstThreadId, uint secondThreadId, bool attach);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint SendInput(uint inputCount, INPUT[] inputs, int inputSize);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern short VkKeyScanW(char character);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern uint MapVirtualKeyW(uint virtualKey, uint mapType);

    private static bool SendKeyboardInput(ushort virtualKey, ushort scanCode, uint flags)
    {
        INPUT[] input = new[] {
            new INPUT {
                Type = INPUT_KEYBOARD,
                Union = new InputUnion {
                    Keyboard = new KEYBDINPUT {
                        VirtualKey = virtualKey,
                        ScanCode = scanCode,
                        Flags = flags,
                        Time = 0,
                        ExtraInfo = IntPtr.Zero
                    }
                }
            }
        };
        return SendInput((uint)input.Length, input, Marshal.SizeOf(typeof(INPUT))) == input.Length;
    }

    private static bool SendPhysicalKeyState(ushort virtualKey, bool keyUp)
    {
        uint scanCode = MapVirtualKeyW(virtualKey, MAPVK_VK_TO_VSC);
        if (scanCode != 0)
        {
            uint flags = KEYEVENTF_SCANCODE | (keyUp ? KEYEVENTF_KEYUP : 0);
            return SendKeyboardInput(0, (ushort)scanCode, flags);
        }
        return SendKeyboardInput(virtualKey, 0, keyUp ? KEYEVENTF_KEYUP : 0);
    }

    private static bool SendPhysicalKey(ushort virtualKey)
    {
        return SendPhysicalKeyState(virtualKey, false) &&
            SendPhysicalKeyState(virtualKey, true);
    }

    private static bool SendConsoleCharacter(char character)
    {
        short mapped = VkKeyScanW(character);
        if (mapped == -1)
            return false;

        ushort virtualKey = (ushort)(mapped & 0xff);
        byte modifiers = (byte)((mapped >> 8) & 0xff);
        ushort[] held = new ushort[3];
        int heldCount = 0;
        try
        {
            if ((modifiers & 1) != 0) {
                if (!SendPhysicalKeyState((ushort)VK_SHIFT, false))
                    return false;
                held[heldCount++] = (ushort)VK_SHIFT;
            }
            if ((modifiers & 2) != 0) {
                if (!SendPhysicalKeyState((ushort)VK_CONTROL, false))
                    return false;
                held[heldCount++] = (ushort)VK_CONTROL;
            }
            if ((modifiers & 4) != 0) {
                if (!SendPhysicalKeyState((ushort)VK_MENU, false))
                    return false;
                held[heldCount++] = (ushort)VK_MENU;
            }
            return SendPhysicalKey(virtualKey);
        }
        finally
        {
            for (int index = heldCount - 1; index >= 0; --index)
                SendPhysicalKeyState(held[index], true);
        }
    }

    private static bool ConsoleCommandFailed(string status)
    {
        LastConsoleCommandStatus = status;
        return false;
    }

    private static bool CaptureFocusState(string stage, IntPtr target)
    {
        IntPtr foreground = GetForegroundWindow();
        uint foregroundProcessId = 0;
        if (foreground != IntPtr.Zero)
        {
            uint ignoredThreadId = GetWindowThreadProcessId(foreground, out foregroundProcessId);
        }
        LastFocusStage = stage;
        LastFocusForegroundProcessId = foregroundProcessId;
        LastFocusTargetForeground = foreground == target;
        return LastFocusTargetForeground;
    }

    private static bool ActivateWithoutForegroundQueue(
        IntPtr hWnd, uint callerThreadId, uint targetThreadId)
    {
        // A desktop-hosted automation process can enumerate the visible target
        // yet have no accessible foreground window. There is therefore no
        // foreground queue to attach. Share only the helper/verified-target
        // queues, retry native activation, and still require the exact target
        // to become foreground before SendInput can run.
        bool attached = callerThreadId != targetThreadId &&
            AttachThreadInput(callerThreadId, targetThreadId, true);
        try
        {
            if (callerThreadId != targetThreadId && !attached)
            {
                CaptureFocusState("target-queue-attach-failed", hWnd);
                return false;
            }
            ShowWindow(hWnd, SW_RESTORE);
            BringWindowToTop(hWnd);
            SetActiveWindow(hWnd);
            SetFocus(hWnd);
            SetForegroundWindow(hWnd);
            Thread.Sleep(250);
            if (CaptureFocusState("no-foreground-queue-activation", hWnd))
                return true;
            SwitchToThisWindow(hWnd, true);
            Thread.Sleep(250);
            return CaptureFocusState("no-foreground-task-switch", hWnd);
        }
        finally
        {
            if (attached)
                AttachThreadInput(callerThreadId, targetThreadId, false);
        }
    }

    private static bool FocusExactWindow(IntPtr hWnd)
    {
        ShowWindow(hWnd, SW_RESTORE);
        BringWindowToTop(hWnd);
        SetForegroundWindow(hWnd);
        Thread.Sleep(250);
        if (CaptureFocusState("direct-activation", hWnd))
            return true;

        IntPtr foreground = GetForegroundWindow();
        uint foregroundProcessId;
        uint targetProcessId;
        uint foregroundThreadId = foreground == IntPtr.Zero
            ? 0
            : GetWindowThreadProcessId(foreground, out foregroundProcessId);
        uint targetThreadId = GetWindowThreadProcessId(hWnd, out targetProcessId);
        uint callerThreadId = GetCurrentThreadId();
        if (targetThreadId == 0 || callerThreadId == 0)
        {
            CaptureFocusState("thread-unavailable", hWnd);
            return false;
        }
        if (foregroundThreadId == 0)
            return ActivateWithoutForegroundQueue(hWnd, callerThreadId, targetThreadId);

        // SetForegroundWindow is called by this managed helper, not by the
        // target game window. Attach both the caller and exact target queue to
        // the current foreground queue, then activate/focus that already
        // verified target. The helper still proves foreground ownership before
        // it emits any system input, so queue attachment cannot redirect keys
        // to another process.
        bool callerAttached = callerThreadId != foregroundThreadId &&
            AttachThreadInput(callerThreadId, foregroundThreadId, true);
        bool targetAttached = targetThreadId != foregroundThreadId &&
            AttachThreadInput(targetThreadId, foregroundThreadId, true);
        try
        {
            if ((callerThreadId != foregroundThreadId && !callerAttached) ||
                (targetThreadId != foregroundThreadId && !targetAttached))
            {
                CaptureFocusState("queue-attach-failed", hWnd);
                return false;
            }
            ShowWindow(hWnd, SW_RESTORE);
            BringWindowToTop(hWnd);
            SetActiveWindow(hWnd);
            SetFocus(hWnd);
            SetForegroundWindow(hWnd);
            Thread.Sleep(250);
            if (CaptureFocusState("queue-activation", hWnd))
                return true;

            // Some desktop hosts reject SetForegroundWindow even after the
            // caller is attached to their input queue. Use the same task-switch
            // activation path a user would invoke, but only for this exact
            // already-verified Rerelease window, then prove focus again before
            // SendInput emits a single key.
            SwitchToThisWindow(hWnd, true);
            Thread.Sleep(250);
            return CaptureFocusState("task-switch-retry", hWnd);
        }
        finally
        {
            if (targetAttached)
                AttachThreadInput(targetThreadId, foregroundThreadId, false);
            if (callerAttached)
                AttachThreadInput(callerThreadId, foregroundThreadId, false);
        }
    }

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
        LastConsoleCommandStatus = "not-attempted";
        LastFocusStage = "not-attempted";
        LastFocusForegroundProcessId = 0;
        LastFocusTargetForeground = false;
        if (hWnd == IntPtr.Zero || String.IsNullOrEmpty(command) || !IsWindowVisible(hWnd))
            return ConsoleCommandFailed("target-unavailable");
        if (!FocusExactWindow(hWnd))
            return ConsoleCommandFailed("foreground-unavailable");
        if (!SendPhysicalKey((ushort)VK_OEM_3))
            return ConsoleCommandFailed("console-toggle-send-failed");
        Thread.Sleep(150);
        foreach (char character in command)
        {
            if (!SendConsoleCharacter(character))
                return ConsoleCommandFailed("character-send-failed");
            Thread.Sleep(5);
        }
        if (!SendPhysicalKey((ushort)VK_RETURN))
            return ConsoleCommandFailed("return-send-failed");
        LastConsoleCommandStatus = "input-submitted";
        return true;
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

function Stop-RunRereleaseProcesses {
    param(
        [Parameter(Mandatory = $true)][string]$ExecutablePath,
        [Parameter(Mandatory = $true)][DateTime]$Started,
        [Parameter(Mandatory = $true)][hashtable]$ObservedProcesses
    )

    # Start-up is preceded by a continuous quiescence interval, so every
    # selected executable newer than this boundary belongs to this run. Query
    # live processes again instead of trusting the original Start-Process
    # object: Steam can replace that object during handoff.
    $minimumStart = $Started.AddSeconds(-2)
    $candidates = @{}
    foreach ($candidate in @(Get-RereleaseProcesses $ExecutablePath)) {
        $candidates[$candidate.Id] = $candidate
    }
    foreach ($observedId in $ObservedProcesses.Keys) {
        try {
            $candidate = Get-Process -Id $observedId -ErrorAction Stop
            if ($candidate.Path -and (Get-ZaeREoFullPath $candidate.Path).Equals(
                $ExecutablePath,
                [StringComparison]::OrdinalIgnoreCase
            )) {
                $candidates[$candidate.Id] = $candidate
            }
        }
        catch {
            # The exact observed process may already have exited.
        }
    }

    foreach ($candidate in @($candidates.Values)) {
        try {
            $candidate.Refresh()
            if ($candidate.HasExited -or $candidate.StartTime.ToUniversalTime() -lt $minimumStart) {
                continue
            }
            $current = Get-Process -Id $candidate.Id -ErrorAction Stop
            if ($current.StartTime.ToUniversalTime() -ge $minimumStart -and
                $current.Path -and (Get-ZaeREoFullPath $current.Path).Equals(
                    $ExecutablePath,
                    [StringComparison]::OrdinalIgnoreCase
                )) {
                Stop-Process -Id $current.Id -Force
                [void]$current.WaitForExit(5000)
            }
        }
        catch {
            # A later residual-process check below records a failed run if the
            # exact verified process cannot be terminated.
        }
    }

    return @(
        Get-RereleaseProcesses $ExecutablePath | Where-Object {
            $_.StartTime.ToUniversalTime() -ge $minimumStart
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
$windowReadyDelay = [TimeSpan]::FromSeconds(1)
# The first process command line must not select the mod or map. The native
# window is made and checked first; only then does the wrapper deliver this
# console command to the verified, exact-PID window.
$runtimeCommands = @(
    "echo $beginMarker",
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
    "+set", "logfile", "2"
)

Write-Host "Runtime smoke plan"
Write-Host "  engine:  $executablePath"
Write-Host "  mod:     $modPath"
Write-Host "  map:     $Map"
Write-Host "  mode:    $(if ($Deathmatch) { 'deathmatch' } else { 'single-player' })"
Write-Host "  zdmflags: $ZdmFlags"
Write-Host "  DM item probe: $([bool]$ProbeDeathmatchItems)"
Write-Host "  command delivery: $(if ($ManualCommandDelivery) { 'manual engine-confirmed' } else { 'foreground-gated system input' })"
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
$modMapCommandDeliveryAttempted = $false
$commandDelivery = "not-attempted"
$windowVerifiedAt = $null
$residualProcessIds = @()
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
                        if ($null -eq $windowVerifiedAt) {
                            $windowVerifiedAt = [DateTime]::UtcNow
                        }
                    }
                }
            }
        }
    }
    if (-not $windowSafetyAborted -and -not $modMapCommandDeliveryAttempted -and
        $verifiedWindowHandles.Count -and $null -ne $windowVerifiedAt -and
        [DateTime]::UtcNow -ge $windowVerifiedAt.Add($windowReadyDelay)) {
        $modMapCommandDeliveryAttempted = $true
        if ($ManualCommandDelivery) {
            $commandDelivery = "manual-awaiting-engine-confirmation"
            Write-Warning "Manual command delivery selected. In the verified windowed Quake II client, open the console and submit exactly:"
            Write-Host "  $runtimeCommand"
        }
        else {
            $modMapCommandInjected = [ZaeREoWindowProbe]::SendConsoleCommand(
                $verifiedWindowHandles[0],
                $runtimeCommand
            )
            $commandDelivery = [ZaeREoWindowProbe]::LastConsoleCommandStatus
            if (-not $modMapCommandInjected) {
                $modMapCommandInjectionFailed = $true
                $windowSafetyAborted = $true
            }
        }
    }
    if (Test-Path -LiteralPath $stdoutPath -PathType Leaf) {
        $currentLog = Get-Content -LiteralPath $stdoutPath -Raw
        $log = if ($null -eq $currentLog) { "" } else { [string]$currentLog }
        $currentBeginIndex = $log.LastIndexOf($beginMarker, [StringComparison]::Ordinal)
        if ($modMapCommandDeliveryAttempted -and $currentBeginIndex -ge 0) {
            $modMapCommandInjected = $true
            $commandDelivery = "engine-confirmed"
        }
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
    $activeProcesses = @(Stop-RunRereleaseProcesses `
        -ExecutablePath $executablePath `
        -Started $started `
        -ObservedProcesses $observedProcesses)
    $residualProcessIds = @(
        foreach ($remainingProcess in $activeProcesses) {
            $remainingProcess.Id
        }
    )
    $residualProcessIds = @($residualProcessIds | Sort-Object -Unique)
}
$finished = [DateTime]::UtcNow

try {
    $process.Refresh()
    if (-not $process.HasExited) {
        [void]$process.WaitForExit(5000)
        $process.Refresh()
    }
    $processExitCode = if ($process.HasExited) { $process.ExitCode } else { -1 }
}
catch {
    $processExitCode = -1
}

# A missing log is itself failed private evidence, not a reason to lose the
# report. The marker fields below remain false and retain the window/cleanup
# observations that explain the failure.
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
    $probeComplete -and
    $residualProcessIds.Count -eq 0

$focusForegroundProcessId = [uint64][ZaeREoWindowProbe]::LastFocusForegroundProcessId
$focusDiagnostic = [ordered]@{
    stage = [string][ZaeREoWindowProbe]::LastFocusStage
    foreground_process_id = if ($focusForegroundProcessId -eq 0) { $null } else { $focusForegroundProcessId }
    target_foreground = [bool][ZaeREoWindowProbe]::LastFocusTargetForeground
}

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
    focus_diagnostic = $focusDiagnostic
    non_windowed_visible_observed = $nonWindowedVisibleObserved
    window_safety_abort = $windowSafetyAborted
    launch_protocol = "two-stage-window-before-mod-map/v1"
    command_delivery = $commandDelivery
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
    residual_process_ids = $residualProcessIds
    console_log = "stdout.txt"
    publication_status = "private-local-only"
}
New-Item -ItemType Directory -Path (Split-Path -Parent $reportPath) -Force | Out-Null
Write-NormalizedJson $reportPath $report

if (-not $passed) {
    throw "Runtime smoke failed; private report: $reportPath"
}
Write-Host "Runtime smoke passed: map=$Map exit=$processExitCode report=$reportPath"
