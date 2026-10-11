# Run explicitly from ordinary owner PowerShell, outside the Codex worker.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$ExpectedCommit,
    [Parameter(Mandatory)][string]$Manifest,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSHA256,
    [Parameter(Mandatory)][string]$Python,
    [Parameter(Mandatory)][switch]$OwnerShell
)
$ErrorActionPreference = 'Stop'
if (-not $OwnerShell) { throw 'Run in ordinary owner PowerShell and declare -OwnerShell.' }
$sourceRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = (Resolve-Path -LiteralPath $Python).Path
$manifestPath = (Resolve-Path -LiteralPath $Manifest).Path
if ((Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ManifestSHA256) { throw 'Manifest hash mismatch' }
$inventory = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($inventory.commit -ne $ExpectedCommit) { throw 'Manifest commit mismatch' }
$actualCommit = & git -C $sourceRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actualCommit.Trim() -ne $ExpectedCommit) { throw 'Source commit mismatch' }
$tracked = @(& git -C $sourceRoot ls-files)
if ($LASTEXITCODE -ne 0) { throw 'Cannot enumerate source' }
if (Compare-Object ($tracked | Sort-Object) (@($inventory.files.path) | Sort-Object)) { throw 'Source inventory mismatch' }
foreach ($file in $inventory.files) {
    $path = [IO.Path]::GetFullPath((Join-Path $sourceRoot $file.path))
    if (-not $path.StartsWith($sourceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Out-of-scope source path' }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { throw "Changed source: $($file.path)" }
}
& git -C $sourceRoot diff --quiet HEAD --
if ($LASTEXITCODE -ne 0) { throw 'Tracked source is dirty' }
$pythonInfo = & $pythonPath -c 'import json,platform,sys; print(json.dumps(dict(version=sys.version,platform=platform.platform(),executable=sys.executable)))'
if ($LASTEXITCODE -ne 0) { throw 'Approved Python unavailable' }
$pythonInfo = $pythonInfo | ConvertFrom-Json
$resultDirectory = Join-Path $sourceRoot ('reports/owner-windows-' + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $resultDirectory | Out-Null
$log = Join-Path $resultDirectory 'standard.txt'
$started = [DateTimeOffset]::UtcNow
$timer = [Diagnostics.Stopwatch]::StartNew()
Push-Location $sourceRoot
try {
    & $pythonPath -m unittest discover -s tests -v *> $log
    $code = $LASTEXITCODE
} finally { Pop-Location; $timer.Stop() }
$text = Get-Content -LiteralPath $log -Raw
$count = $null
$testSeconds = $null
if ($text -match 'Ran (\d+) tests? in ([0-9.]+)s') {
    $count = [int]$Matches[1]; $testSeconds = [double]::Parse($Matches[2], [Globalization.CultureInfo]::InvariantCulture)
}
$failures = 0; $errors = 0
if ($text -match 'failures=(\d+)') { $failures = [int]$Matches[1] }
if ($text -match 'errors=(\d+)') { $errors = [int]$Matches[1] }
$unchanged = $true
foreach ($file in $inventory.files) {
    if ((Get-FileHash -LiteralPath (Join-Path $sourceRoot $file.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { $unchanged = $false }
}
$passed = ($code -eq 0 -and $null -ne $count -and $text -match '(?m)^OK\s*$' -and $unchanged)
$report = [ordered]@{
    layer = 'OWNER_WINDOWS'; status = $(if ($passed) { 'PASS' } else { 'FAIL' })
    context = 'Owner-declared ordinary shell; this script does not authenticate the operator or token'
    source_commit = $ExpectedCommit; source_manifest_sha256 = $ManifestSHA256
    source_unchanged = $unchanged; python = $pythonInfo; powershell = $PSVersionTable.PSVersion.ToString()
    windows = [Environment]::OSVersion.VersionString; command = 'python -m unittest discover -s tests -v'
    started_utc = $started.ToString('o'); finished_utc = [DateTimeOffset]::UtcNow.ToString('o')
    elapsed_seconds = $timer.Elapsed.TotalSeconds; test_seconds = $testSeconds
    tests = $count; failures = $failures; errors = $errors; exit_code = $code
    log_sha256 = (Get-FileHash -LiteralPath $log -Algorithm SHA256).Hash.ToLowerInvariant()
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $resultDirectory 'result.json') -Encoding utf8
Write-Output $resultDirectory
if (-not $passed) { exit 1 }
