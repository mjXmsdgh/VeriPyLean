# generate_stubs.ps1
# Script to generate .pyi type stub files using stubgen for token optimization

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$outputDir = Join-Path $scriptDir "typings"

# Determine Python executable path
$pythonExe = ""
if (Test-Path "$scriptDir\.venv\Scripts\python.exe") {
    $pythonExe = "$scriptDir\.venv\Scripts\python.exe"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
} else {
    Write-Error "Python executable not found. Please activate your virtual environment or install Python."
    exit 1
}

Write-Host "==> Generating type stubs (.pyi) with stubgen..." -ForegroundColor Cyan

# Clean existing typings directory if present
if (Test-Path $outputDir) {
    Write-Host "Cleaning existing typings directory: $outputDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $outputDir
}

# Run stubgen via python entrypoint
& $pythonExe -c "import mypy.stubgen; mypy.stubgen.main()" --parse-only --include-private --include-docstrings -p app -o $outputDir

if ($LASTEXITCODE -eq 0) {
    $stubCount = (Get-ChildItem -Path $outputDir -Recurse -Filter "*.pyi").Count
    Write-Host "`n[SUCCESS] Successfully generated $stubCount stub files in '$outputDir'." -ForegroundColor Green
    Write-Host "Tip: Pass these .pyi files instead of full .py files to AI prompts to save tokens!" -ForegroundColor DarkGray
} else {
    Write-Error "[ERROR] stubgen failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
