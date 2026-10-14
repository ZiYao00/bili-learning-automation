# Agent-only helper: plan by default; -Apply requires the user's authorization
# for the specific external target. Never deletes or replaces an existing path.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Target,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'

function Report([string]$status, [string]$message, [string]$sourcePath, [string]$targetPath) {
    [pscustomobject]@{
        status = $status
        message = $message
        source = $sourcePath
        target = $targetPath
    } | ConvertTo-Json -Compress -Depth 3
}

try {
    if (-not [IO.Path]::IsPathRooted($Source) -or -not [IO.Path]::IsPathRooted($Target)) {
        throw 'Source and Target must both be absolute paths.'
    }
    $sourceItem = Get-Item -LiteralPath $Source -Force -ErrorAction Stop
    if (-not $sourceItem.PSIsContainer) { throw 'Source is not an existing directory.' }
    $sourcePath = [IO.Path]::GetFullPath($sourceItem.FullName).TrimEnd('\')
    $targetPath = [IO.Path]::GetFullPath($Target).TrimEnd('\')
    if ([string]::Equals($sourcePath, $targetPath, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Source and Target cannot be identical.'
    }
    if ($targetPath.StartsWith($sourcePath + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Target cannot be nested inside Source; a junction loop is unsafe.'
    }

    $existing = Get-Item -LiteralPath $targetPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        $linkedToSource = $false
        if ($existing.LinkType -eq 'Junction' -and $existing.Target) {
            $actualTarget = [IO.Path]::GetFullPath([string]@($existing.Target)[0]).TrimEnd('\')
            $linkedToSource = [string]::Equals(
                $actualTarget, $sourcePath, [StringComparison]::OrdinalIgnoreCase
            )
        }
        if ($linkedToSource) {
            Report 'already_installed' 'Correct junction already exists. No changes made.' $sourcePath $targetPath
            exit 0
        }
        Report 'conflict' 'Target exists; preserving it without changes.' $sourcePath $targetPath
        exit 2
    }

    if (-not $Apply) {
        Report 'planned' 'No changes made. Ask for authorization before using -Apply.' $sourcePath $targetPath
        exit 0
    }

    $parent = Split-Path -Parent $targetPath
    New-Item -ItemType Directory -Path $parent -Force -ErrorAction Stop | Out-Null
    if ($null -ne (Get-Item -LiteralPath $targetPath -Force -ErrorAction SilentlyContinue)) {
        Report 'conflict' 'Target appeared during installation; preserving it.' $sourcePath $targetPath
        exit 2
    }
    New-Item -ItemType Junction -Path $targetPath -Target $sourcePath -ErrorAction Stop | Out-Null
    $verified = Get-Item -LiteralPath $targetPath -Force -ErrorAction Stop
    if ($verified.LinkType -ne 'Junction') {
        throw 'Created link is not a Junction; inspect it manually, no automatic deletion.'
    }
    $verifiedTarget = [IO.Path]::GetFullPath([string]@($verified.Target)[0]).TrimEnd('\')
    if (-not [string]::Equals($verifiedTarget, $sourcePath, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Created Junction target differs from expected source; inspect manually.'
    }
    Report 'installed' 'Junction created and verified.' $sourcePath $targetPath
    exit 0
} catch {
    Report 'failed' $_.Exception.Message $Source $Target
    exit 2
}
