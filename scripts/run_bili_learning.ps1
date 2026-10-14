# Agent-only launcher and Python preflight; NOT a double-click installer.
[CmdletBinding()]
param(
    [switch]$ProbeOnly,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
. (Join-Path $PSScriptRoot 'python_runtime.ps1')
$runtime = Resolve-BiliPython -ProjectRoot $projectRoot
if ($null -eq $runtime) {
    [pscustomobject]@{
        schema_version = 1
        status = 'python_required'
        required = '>=3.10,<4'
        message = 'No validated Python >=3.10 found. Agent must obtain permission before installing Python 3.12.'
        install_url = 'https://www.python.org/downloads/windows/'
        changes_made = $false
    } | ConvertTo-Json -Compress
    exit 2
}
if ($ProbeOnly) {
    [pscustomobject]@{
        schema_version = 1
        status = 'ready'
        python_version = $runtime.version
        source = $runtime.source
        executable = $runtime.executable
        prefix_args = @($runtime.prefix_args)
        changes_made = $false
    } | ConvertTo-Json -Compress -Depth 4
    exit 0
}

$python = [string]$runtime.executable
$prefix = @($runtime.prefix_args)
$script = Join-Path $PSScriptRoot 'run_bili_learning.py'
$result = Invoke-BiliPythonProbe -Executable $python -Arguments (@($prefix) + @($script) + @($CliArgs)) -TimeoutMilliseconds -1
if ($null -eq $result) { throw 'Python process could not complete; no application output is available.' }
if ($result.stdout) { [Console]::Out.Write($result.stdout) }
if ($result.stderr) { [Console]::Error.Write($result.stderr) }
exit [int]$result.exit_code
