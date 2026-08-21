[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [ValidateSet(
    "90-full-snapshots",
    "91-note-backups",
    "95-agent-adapters"
  )]
  [string]$Category,

  [Parameter(Mandatory)]
  [ValidatePattern("^[a-z0-9][a-z0-9-]*$")]
  [string]$Label
)

# 在项目备份目录内创建一个源文件级回滚 ZIP。
# 不要改用 Compress-Archive 递归压缩文件列表：那曾把路径打平、
# 连同 .git 对象和早期 ZIP 一起打包，产生嵌套的 100+ MB 备份。
# ZipArchive 保持仓库相对路径，下方显式目录过滤器排除元数据与既有备份。

# Windows PowerShell 5.1 不会提前解析脚本后文声明的类型，所以先在顶部
# 加载程序集，并用运行时解析的字符串常量引用枚举。PS 5.1 与 pwsh 7+
# 因此可以完全一致地运行本脚本。
Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop | Out-Null

$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$backupRoot = Join-Path $repoRoot ".codex-backups"
$categoryRoot = Join-Path $backupRoot $Category
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archivePath = Join-Path $categoryRoot "bili-learning-automation-before-$Label-$timestamp.zip"

if (!(Test-Path -LiteralPath $categoryRoot)) {
  New-Item -ItemType Directory -Path $categoryRoot | Out-Null
}
if (Test-Path -LiteralPath $archivePath) {
  throw "Backup destination already exists: $archivePath"
}

# 计算仓库相对路径，不依赖 [System.IO.Path]::GetRelativePath
# （Windows PowerShell 5.1 / .NET Framework 4.x 中不存在）。
# 手动归一化保持 ZIP 内为 POSIX 风格的仓库相对条目名。
function Get-RepoRelativePath {
  param(
    [Parameter(Mandatory)][string]$Root,
    [Parameter(Mandatory)][string]$FullPath
  )
  $rootNorm = $Root.TrimEnd('\', '/')
  if (-not $FullPath.StartsWith($rootNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path is not under the repository root: $FullPath (root=$rootNorm)"
  }
  $rel = $FullPath.Substring($rootNorm.Length)
  return $rel.TrimStart('\', '/')
}

# 排除项（详见 .codex-backups/README.md）：
# - 版本库元数据与备份根目录自身；
# - 可重建的环境与缓存；
# - key/ 凭据：Cookie 内容永不进入归档；
# - .runtime/ 临时任务目录，由 finalizer 管理生命周期。
$excludedDirectories = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($name in @(".git", ".codex-backups", "__pycache__", "node_modules", ".venv", "venv", "env", ".pytest_cache", ".ruff_cache", "key", ".runtime")) {
  [void]$excludedDirectories.Add($name)
}

$files = Get-ChildItem -LiteralPath $repoRoot -Force -Recurse -File | Where-Object {
  $relative = Get-RepoRelativePath -Root $repoRoot -FullPath $_.FullName
  -not (($relative -split "[\\/]") | Where-Object { $excludedDirectories.Contains($_) }) -and
  $_.Extension -notin @(".zip", ".7z", ".rar", ".tar", ".gz")
}

# 通过字符串形式解析枚举值，避免 PS 5.1 在脚本加载期解析
# `[System.IO.Compression.ZipArchiveMode]::Create`。两种运行时最终
# 访问相同的底层成员。
$zipCreateMode = [System.Enum]::Parse([Type]"System.IO.Compression.ZipArchiveMode", "Create")
$zipCompressionLevel = [System.Enum]::Parse([Type]"System.IO.Compression.CompressionLevel", "Optimal")
$archive = [System.IO.Compression.ZipFile]::Open($archivePath, $zipCreateMode)
try {
  foreach ($file in $files) {
    $entryName = (Get-RepoRelativePath -Root $repoRoot -FullPath $file.FullName).Replace("\", "/")
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
      $archive,
      $file.FullName,
      $entryName,
      $zipCompressionLevel
    ) | Out-Null
  }
} finally {
  $archive.Dispose()
}

# 归档自检：任何被排除路径混入即判定失败，保留该文件供检查，
# 不得作为回滚点使用。
$inspection = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
try {
  $forbidden = @($inspection.Entries | Where-Object {
    $_.FullName -match "(^|/)(\.git|\.codex-backups|__pycache__|node_modules|\.venv|venv|env|\.pytest_cache|\.ruff_cache|key|\.runtime)(/|$)" -or
    $_.FullName -match "\.(zip|7z|rar|tar|gz)$"
  })
  if ($forbidden.Count) {
    throw "Backup contains excluded paths; retain this file for inspection and do not use it as a rollback point: $archivePath"
  }
  Write-Output ("Created source backup: {0} ({1} files)" -f $archivePath, $inspection.Entries.Count)
} finally {
  $inspection.Dispose()
}
