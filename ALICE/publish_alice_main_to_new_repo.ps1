param(
    [string]$SourcePath = "d:\ALICE(NEW)\Alice-main07",
    [string]$TargetRepoUrl = "https://github.com/BLx-Ankush/Alice-Main.git",
    [string]$WorkingClonePath = "d:\ALICE(NEW)\Alice-main-clean-publish"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting ALICE main-code publish workflow..." -ForegroundColor Cyan

if (-not (Test-Path $SourcePath)) {
    throw "Source path not found: $SourcePath"
}

if (Test-Path $WorkingClonePath) {
    Write-Host "Removing existing working clone: $WorkingClonePath" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $WorkingClonePath
}

Write-Host "Cloning target repository..." -ForegroundColor Cyan
git clone $TargetRepoUrl $WorkingClonePath

Write-Host "Cleaning repository contents (preserving .git)..." -ForegroundColor Cyan
Get-ChildItem -Path $WorkingClonePath -Force |
    Where-Object { $_.Name -ne ".git" } |
    Remove-Item -Recurse -Force

$rootFiles = @(
    "README.md",
    "alice_trigger.py",
    "start_alice.bat"
)

$rootDirs = @(
    "Alice_code",
    "agent-starter-react"
)

Write-Host "Copying main ALICE files..." -ForegroundColor Cyan
foreach ($file in $rootFiles) {
    $srcFile = Join-Path $SourcePath $file
    if (Test-Path $srcFile) {
        Copy-Item -Path $srcFile -Destination (Join-Path $WorkingClonePath $file) -Force
    }
}

foreach ($dir in $rootDirs) {
    $srcDir = Join-Path $SourcePath $dir
    if (Test-Path $srcDir) {
        Copy-Item -Path $srcDir -Destination (Join-Path $WorkingClonePath $dir) -Recurse -Force
    }
}

$removeDirs = @(
    "tests",
    "__pycache__",
    ".pytest_cache",
    "venv_new",
    "temp_alice_files",
    ".next",
    "dist",
    "build"
)

$removeFilePatterns = @(
    "test*.py",
    "*test*.py",
    "pytest.ini",
    "*RESULTS*.md",
    "*SUMMARY*.md",
    "*automation_test*.txt",
    "control_log.txt",
    "ALICE_Submission.zip"
)

Write-Host "Removing test and result artifacts..." -ForegroundColor Cyan
foreach ($dirName in $removeDirs) {
    Get-ChildItem -Path $WorkingClonePath -Recurse -Force -Directory -Filter $dirName -ErrorAction SilentlyContinue |
        ForEach-Object {
            Remove-Item -Recurse -Force $_.FullName
        }
}

foreach ($pattern in $removeFilePatterns) {
    Get-ChildItem -Path $WorkingClonePath -Recurse -Force -File -Filter $pattern -ErrorAction SilentlyContinue |
        ForEach-Object {
            Remove-Item -Force $_.FullName
        }
}

$now = Get-Date
Write-Host "Normalizing all file/folder timestamps to: $($now.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Get-ChildItem -Path $WorkingClonePath -Recurse -Force |
    ForEach-Object {
        $_.CreationTime = $now
        $_.LastWriteTime = $now
        $_.LastAccessTime = $now
    }

Write-Host "Creating commit and pushing..." -ForegroundColor Cyan
git -C $WorkingClonePath add .

if (-not (git -C $WorkingClonePath diff --cached --quiet)) {
    git -C $WorkingClonePath commit -m "Initial ALICE main code import (tests/results removed; timestamps normalized)"
}
else {
    Write-Host "No staged changes detected; skipping commit." -ForegroundColor Yellow
}

$branch = (git -C $WorkingClonePath rev-parse --abbrev-ref HEAD).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    $branch = "main"
}

git -C $WorkingClonePath push -u origin $branch

Write-Host "Publish completed successfully." -ForegroundColor Green
Write-Host "Working clone path: $WorkingClonePath" -ForegroundColor Green