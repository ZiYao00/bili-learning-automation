$ErrorActionPreference = 'Stop'
$bridgeArgs = @($args)

$skillDir = Split-Path $PSScriptRoot -Parent
$skillItem = Get-Item -LiteralPath $skillDir
$skillSource = if ($skillItem.LinkType -and $skillItem.Target) {
  [string]$skillItem.Target
} else {
  $skillDir
}

$projectRoot = Split-Path (Split-Path $skillSource -Parent) -Parent
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$bridge = Join-Path $skillSource 'scripts\local_bridge.py'

if (-not (Test-Path -LiteralPath $bridge)) {
  throw "Local Agent bridge not found: $bridge"
}

$env:PYTHONPATH = $null

if (Test-Path -LiteralPath $python) {
  & $python $bridge @bridgeArgs
  exit $LASTEXITCODE
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
  & $pythonCommand.Source $bridge @bridgeArgs
  exit $LASTEXITCODE
}

$pyCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pyCommand) {
  & $pyCommand.Source -3 $bridge @bridgeArgs
  exit $LASTEXITCODE
}

throw 'Python 3.10+ not found. Install Python or create the project .venv first.'
