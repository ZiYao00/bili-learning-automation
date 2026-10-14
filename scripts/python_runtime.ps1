# Read-only Python resolver shared by the project CLI and canonical Agent bridge.
# PowerShell 5.1 compatible. Does not install Python, create venvs, or modify PATH.
function ConvertTo-BiliWindowsArgument {
    param([AllowEmptyString()][string]$Value)
    $quoted = '"'
    $slashes = 0
    foreach ($character in $Value.ToCharArray()) {
        if ($character -eq '\') {
            $slashes += 1
            continue
        }
        if ($character -eq '"') {
            $quoted += ('\' * (2 * $slashes + 1)) + '"'
        } else {
            $quoted += ('\' * $slashes) + $character
        }
        $slashes = 0
    }
    return $quoted + ('\' * (2 * $slashes)) + '"'
}

function Invoke-BiliPythonProbe {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$Arguments = @(),
        [int]$TimeoutMilliseconds = 8000
    )
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $Executable
    $escaped = @($Arguments | ForEach-Object { ConvertTo-BiliWindowsArgument -Value $_ })
    $start.Arguments = $escaped -join ' '
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardOutputEncoding = [Text.Encoding]::UTF8
    $start.StandardErrorEncoding = [Text.Encoding]::UTF8
    $start.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $start.EnvironmentVariables['PYTHONPATH'] = ''
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { return $null }
        # Consume both redirected streams asynchronously to prevent pipe deadlocks.
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            $process.Kill()
            $process.WaitForExit()
            return $null
        }
        return [pscustomobject]@{
            stdout = $stdoutTask.GetAwaiter().GetResult()
            stderr = $stderrTask.GetAwaiter().GetResult()
            exit_code = $process.ExitCode
        }
    } catch {
        return $null
    } finally {
        $process.Dispose()
    }
}

function Test-BiliPythonCandidate {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)][string]$Origin
    )
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        return $null
    }
    $probe = "import sys; v=sys.version_info; print('%d.%d.%d' % v[:3]); sys.exit(0 if (3, 10) <= v[:2] < (4, 0) else 23)"
    $result = Invoke-BiliPythonProbe -Executable $Executable -Arguments (@($Arguments) + @('-c', $probe))
    if ($null -eq $result -or $result.exit_code -ne 0) { return $null }
    $version = (($result.stdout.Trim() -split '\r?\n') | Select-Object -Last 1)
    if ($version -notmatch '^3\.\d+\.\d+$') { return $null }
    return [pscustomobject]@{
        executable = $Executable
        prefix_args = @($Arguments)
        version = $version
        source = $Origin
    }
}

function Resolve-BiliPython {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $root = [IO.Path]::GetFullPath($ProjectRoot)
    # An Agent may supply an independently installed interpreter without
    # changing global PATH or writing a machine-specific project config.
    if ($env:BILI_LEARNING_PYTHON) {
        return Test-BiliPythonCandidate -Executable ([Environment]::ExpandEnvironmentVariables($env:BILI_LEARNING_PYTHON)) -Origin 'explicit_env'
    }
    $localPython = Join-Path $root '.venv\Scripts\python.exe'
    $local = Test-BiliPythonCandidate -Executable $localPython -Origin 'project_venv'
    if ($null -ne $local) { return $local }

    # Avoid Windows Store execution aliases which can trigger an installer UI.
    foreach ($commandName in @('python', 'python3')) {
        $cmd = Get-Command -Name $commandName -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -eq $cmd) { continue }
        $path = [string]$cmd.Source
        if ($path -match '(?i)[\\/]Microsoft[\\/]WindowsApps[\\/]') { continue }
        $candidate = Test-BiliPythonCandidate -Executable $path -Origin "system:$commandName"
        if ($null -ne $candidate) { return $candidate }
    }

    # Only query the installed inventory before attempting a py launcher.
    $py = Get-Command -Name py -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $py) { return $null }
    $pyPath = [string]$py.Source
    if ($pyPath -match '(?i)[\\/]Microsoft[\\/]WindowsApps[\\/]') { return $null }
    $found = Invoke-BiliPythonProbe -Executable $pyPath -Arguments @('-0p')
    if ($null -eq $found -or $found.exit_code -ne 0) { return $null }
    $inventory = $found.stdout + $found.stderr
    foreach ($minor in @(12, 11, 10, 13, 14, 15)) {
        if ($inventory -notmatch "(?m)(?:^|\s)-(?:V:)?3\.$minor(?:\D|$)") { continue }
        $candidate = Test-BiliPythonCandidate -Executable $pyPath -Arguments @("-3.$minor") -Origin 'py_launcher'
        if ($null -ne $candidate) { return $candidate }
    }
    return $null
}
