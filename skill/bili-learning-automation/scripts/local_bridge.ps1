$ErrorActionPreference = 'Stop'
$bridgeArgs = @($args)

$skillDir = Split-Path $PSScriptRoot -Parent
$skillItem = Get-Item -LiteralPath $skillDir
$skillSource = if ($skillItem.LinkType -and $skillItem.Target) {
  [string]@($skillItem.Target)[0]
} else {
  $skillDir
}

$projectRoot = Split-Path (Split-Path $skillSource -Parent) -Parent
$bridge = Join-Path $skillSource 'scripts\local_bridge.py'

if (-not (Test-Path -LiteralPath $bridge)) {
  throw "Local Agent bridge not found: $bridge"
}

. (Join-Path $projectRoot 'scripts\python_runtime.ps1')
$runtime = Resolve-BiliPython -ProjectRoot $projectRoot
if ($null -eq $runtime) {
  throw 'Python 3.10+ not found. Ask the Agent to run scripts/run_bili_learning.ps1 -ProbeOnly; an authorized Python install is required.'
}
$python = [string]$runtime.executable
$prefix = @($runtime.prefix_args)
$result = Invoke-BiliPythonProbe -Executable $python -Arguments (@($prefix) + @($bridge) + @($bridgeArgs)) -TimeoutMilliseconds -1
if ($null -eq $result) { throw 'Python Agent bridge failed before returning a result.' }
if ($result.stdout) { [Console]::Out.Write($result.stdout) }
if ($result.stderr) { [Console]::Error.Write($result.stderr) }
exit [int]$result.exit_code
