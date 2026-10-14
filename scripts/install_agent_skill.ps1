# Agent-only Windows Skill link installer. Plan is read-only until -Apply is set.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Codex', 'Hermes', 'WorkBuddy')]
    [string]$Agent,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'

if (-not $env:USERPROFILE -or -not $env:LOCALAPPDATA) {
    throw 'Windows USERPROFILE and LOCALAPPDATA environment variables are required.'
}
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$sourcePath = Join-Path $projectRoot 'skill\bili-learning-automation'

switch ($Agent) {
    'Codex' {
        $targetPath = Join-Path $env:USERPROFILE '.agents\skills\bili-learning-automation'
    }
    'Hermes' {
        $targetPath = Join-Path $env:LOCALAPPDATA 'hermes\skills\bili-learning-automation'
    }
    'WorkBuddy' {
        $targetPath = Join-Path $env:USERPROFILE '.workbuddy\skills\bili-learning-automation'
    }
}

& (Join-Path $PSScriptRoot 'ensure_junction.ps1') -Source $sourcePath -Target $targetPath -Apply:$Apply
exit $LASTEXITCODE
