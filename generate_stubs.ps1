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

function Format-StubEllipsis {
    <#
    .SYNOPSIS
        Appends '...' to functions and methods whose body only contains a docstring (PEP 484 compliance).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        
        [Parameter(Mandatory = $true)]
        [string]$TargetDir
    )

    Write-Host "==> Post-processing stubs for PEP 484 compliance (appending '...' to docstrings)..." -ForegroundColor Cyan

    $pythonCode = @'
import ast
import os
import sys

def patch_pyi_file(path: str) -> int:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    try:
        tree = ast.parse(src)
    except Exception as e:
        print(f"Error parsing {path}: {e}", file=sys.stderr)
        return 0

    insertions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (
                len(body) == 1
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                end_line = getattr(body[0], "end_lineno", body[0].lineno)
                indent = node.col_offset + 4
                insertions.append((end_line, indent))

    if not insertions:
        return 0

    lines = src.splitlines(keepends=True)
    insertions.sort(key=lambda x: x[0], reverse=True)
    for end_line, indent in insertions:
        lines.insert(end_line, f"{' ' * indent}...\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(lines))

    return len(insertions)

target_dir = sys.argv[1]
total_patched = 0
files_patched = 0
for root, _, files in os.walk(target_dir):
    for file in files:
        if file.endswith(".pyi"):
            count = patch_pyi_file(os.path.join(root, file))
            if count > 0:
                total_patched += count
                files_patched += 1

print(f"[PEP 484] Successfully appended '...' to {total_patched} function(s) across {files_patched} stub file(s).")
'@

    $pythonCode | & $PythonExe - $TargetDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[ERROR] Format-StubEllipsis post-processing failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Write-Host "==> Generating type stubs (.pyi) with stubgen..." -ForegroundColor Cyan

# Clean existing typings directory if present
if (Test-Path $outputDir) {
    Write-Host "Cleaning existing typings directory: $outputDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $outputDir
}

# Run stubgen via python entrypoint (removed --parse-only to allow semantic analysis for proper Enum member definitions)
& $pythonExe -c "import mypy.stubgen; mypy.stubgen.main()" --include-private --include-docstrings -p app -o $outputDir

if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] stubgen failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

# Post-process stubs to ensure PEP 484 compliance
Format-StubEllipsis -PythonExe $pythonExe -TargetDir $outputDir

# Verify stubs with mypy
Write-Host "==> Verifying stubs with mypy..." -ForegroundColor Cyan
& $pythonExe -m mypy typings
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] mypy verification failed on typings with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

$stubCount = (Get-ChildItem -Path $outputDir -Recurse -Filter "*.pyi").Count
Write-Host "`n[SUCCESS] Successfully generated and verified $stubCount stub files in '$outputDir'." -ForegroundColor Green
Write-Host "Tip: Pass these .pyi files instead of full .py files to AI prompts to save tokens!" -ForegroundColor DarkGray
