param(
    [Parameter(Mandatory=$true)]
    [string]$VideoPath,
    [Parameter(Mandatory=$true)]
    [string]$Caption
)

$ErrorActionPreference = "Stop"
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$UploaderPy = Join-Path $BaseDir "upload_instagram.py"

$PyExe = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $PyExe)) {
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) { $PyExe = $found.Source }
}

if (-not (Test-Path $PyExe)) {
    Write-Host "[HATA] Python 3.12 bulunamadi."
    exit 1
}

& $PyExe $UploaderPy $VideoPath $Caption
