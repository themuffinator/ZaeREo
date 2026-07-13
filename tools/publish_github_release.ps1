[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "High")]
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$ArchivePath,
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$ChecksumPath,
    [string]$SymbolsPath = "",
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Repository = "",
    [ValidateSet("Stable", "Nightly")][string]$Channel = "Stable",
    [string]$ExpectedBranch = "main",
    [string]$ExpectedCommit = "",
    [switch]$Prerelease,
    [switch]$Publish,
    [switch]$UseExistingTag,
    [switch]$AllowDetachedHead,
    [switch]$ReplaceExistingAssets,
    [switch]$ConfirmRecovery
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Phase-0 containment. This file deliberately contains no GitHub CLI, REST,
# tag, asset-upload, or release implementation. Publication may only be
# reintroduced together with the versioned, machine-readable distribution
# policy and readiness report required by the roadmap. A prose acknowledgement
# or command-line switch is not a gate.
throw "REMOTE_PUBLICATION_DISABLED: gameplay-tree GitHub publication is disabled until the machine-readable distribution policy and readiness gate are implemented and verified. No GitHub state was read or modified."
