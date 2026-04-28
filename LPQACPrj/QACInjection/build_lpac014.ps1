# LPAC014 Project Build Script
# Build Debug_FLASH_C16 configuration using CDS tool
# This script can be placed in any location

# ========================================
# Configuration - Modify these paths as needed
# ========================================
$CDS_TOOL_PATH = "D:\DevTools\CVM_Design_Studio"
$PROJECT_PATH = "F:\SourceCode\LP27\LPAC014\cds"
$PROJECT_NAME = "LPAC014_Application"
$BUILD_CONFIG = "Debug_FLASH_C16"
# ========================================

# Find CDS executable
$CDS_EXE = $null
$possibleExes = @("cds.exe", "eclipse.exe", "eclipsec.exe")
foreach ($exeName in $possibleExes) {
    $exePath = Join-Path $CDS_TOOL_PATH $exeName
    if (Test-Path $exePath) {
        $CDS_EXE = $exePath
        break
    }
}

if (-not $CDS_EXE) {
    Write-Host "Error: CDS tool executable not found" -ForegroundColor Red
    Write-Host "Please check path: $CDS_TOOL_PATH" -ForegroundColor Yellow
    exit 1
}

# Check project path
if (-not (Test-Path $PROJECT_PATH)) {
    Write-Host "Error: Project path does not exist: $PROJECT_PATH" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LPAC014 Project Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CDS Tool Path: $CDS_TOOL_PATH" -ForegroundColor Green
Write-Host "Project Path: $PROJECT_PATH" -ForegroundColor Green
Write-Host "Project Name: $PROJECT_NAME" -ForegroundColor Green
Write-Host "Build Config: $BUILD_CONFIG" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Calculate workspace path (parent directory of project)
$WORKSPACE = Split-Path -Parent $PROJECT_PATH

Write-Host "Starting build via CDS tool..." -ForegroundColor Yellow
Write-Host "Workspace: $WORKSPACE" -ForegroundColor Gray
Write-Host ""

# Build using Eclipse headless build
# -nosplash: No splash screen
# -application: Use headless build application
# -data: Workspace location
# -import: Import project (if not already imported)
# -cleanBuild: Clean before building
$buildArgs = @(
    "-nosplash",
    "-application", "org.eclipse.cdt.managedbuilder.core.headlessbuild",
    "-data", "`"$WORKSPACE`"",
    "-import", "`"$PROJECT_PATH`"",
    "-cleanBuild", "`"$PROJECT_NAME/$BUILD_CONFIG`""
)

Write-Host "Executing: $CDS_EXE $($buildArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

try {
    $process = Start-Process -FilePath $CDS_EXE -ArgumentList $buildArgs -Wait -NoNewWindow -PassThru
    
    if ($process.ExitCode -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Build completed successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        exit 0
    } else {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "Build failed with exit code: $($process.ExitCode)" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        exit $process.ExitCode
    }
} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Build process encountered an error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
