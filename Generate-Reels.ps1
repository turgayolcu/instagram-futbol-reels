param(
    [ValidateSet("odds", "coupon", "results")]
    [string]$Mode = "odds",
    [ValidateSet("spor", "tjk", "millipiyango")]
    [string]$Category = "spor",
    [string]$Theme = "default",
    [string]$DataJsonPath = "",
    [int]$DurationSec = 10
)

$ErrorActionPreference = "Stop"
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FetcherPy = Join-Path $BaseDir "cloud_fetcher.py"
$MotionPy = Join-Path $BaseDir "motion_reels.py"

$PyExe = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $PyExe)) {
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) { $PyExe = $found.Source }
}

if ($DataJsonPath -eq "") {
    # Her calistiginda once resmi sportsbookv2.iddaa.com API'sinden anlik gercek bulteni ve oranlari cek!
    & $PyExe $FetcherPy
    & $PyExe $MotionPy --mode $Mode --category $Category
} else {
    & $PyExe $MotionPy --mode $Mode --category $Category --data $DataJsonPath
}
