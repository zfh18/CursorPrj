@echo off
REM LPAC014 Project Build Script
REM Build Debug_FLASH_C16 configuration using CDS tool
REM This script can be placed in any location

REM ========================================
REM Configuration - Modify these paths as needed
REM ========================================
set "CDS_TOOL_PATH=D:\DevTools\CVM_Design_Studio"
set "PROJECT_PATH=F:\SourceCode\LP27\LPAC014\cds"
set "PROJECT_NAME=LPAC014_Application"
set "BUILD_CONFIG=Debug_FLASH_C16"
REM ========================================

REM Find Java executable and launcher jar
set "JAVA_EXE="
set "LAUNCHER_JAR="

REM Try to find Java from Eclipse's bundled JRE
if exist "%CDS_TOOL_PATH%\plugins\org.eclipse.justj.openjdk.hotspot.jre.full.win32.x86_64_17.0.3.v20220515-1416\jre\bin\java.exe" (
    set "JAVA_EXE=%CDS_TOOL_PATH%\plugins\org.eclipse.justj.openjdk.hotspot.jre.full.win32.x86_64_17.0.3.v20220515-1416\jre\bin\java.exe"
    goto :found_java
)

REM Try system Java
where java >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "JAVA_EXE=java"
    goto :found_java
)

echo Error: Java executable not found
echo Please check if Java is installed or CDS tool path is correct: %CDS_TOOL_PATH%
pause
exit /b 1

:found_java
REM Find Eclipse launcher jar
if exist "%CDS_TOOL_PATH%\plugins\org.eclipse.equinox.launcher_1.6.400.v20210924-0641.jar" (
    set "LAUNCHER_JAR=%CDS_TOOL_PATH%\plugins\org.eclipse.equinox.launcher_1.6.400.v20210924-0641.jar"
    goto :found_launcher
)

echo Error: Eclipse launcher jar not found
echo Please check CDS tool path: %CDS_TOOL_PATH%
pause
exit /b 1

:found_launcher
REM Check project path
if not exist "%PROJECT_PATH%" (
    echo Error: Project path does not exist: %PROJECT_PATH%
    pause
    exit /b 1
)

echo ========================================
echo LPAC014 Project Build Script
echo ========================================
echo CDS Tool Path: %CDS_TOOL_PATH%
echo Project Path: %PROJECT_PATH%
echo Project Name: %PROJECT_NAME%
echo Build Config: %BUILD_CONFIG%
echo ========================================
echo.

REM Use a dedicated workspace under script directory
set "SCRIPT_DIR=%~dp0"
set "WORKSPACE=%SCRIPT_DIR%workspace"
if not exist "%WORKSPACE%" mkdir "%WORKSPACE%"

REM Parse arguments
set "BUILD_CMD=-build"
set "DO_GUI=0"
set "GUI_ONLY=0"
set "VERBOSE=0"
set "USE_CDS_EXE=0"
for %%A in (%*) do (
    if /I "%%~A"=="-cleanBuild" set "BUILD_CMD=-cleanBuild"
    if /I "%%~A"=="-clean" set "BUILD_CMD=-cleanBuild"
    if /I "%%~A"=="-gui" set "DO_GUI=1"
    if /I "%%~A"=="-guiOnly" set "GUI_ONLY=1"
    if /I "%%~A"=="-verbose" set "VERBOSE=1"
    if /I "%%~A"=="-useCdsExe" set "USE_CDS_EXE=1"
)

REM Find CDS GUI executable for optional UI launch
set "CDS_GUI_EXE="
if exist "%CDS_TOOL_PATH%\cds.exe" set "CDS_GUI_EXE=%CDS_TOOL_PATH%\cds.exe"
if not defined CDS_GUI_EXE if exist "%CDS_TOOL_PATH%\eclipse.exe" set "CDS_GUI_EXE=%CDS_TOOL_PATH%\eclipse.exe"

if "%GUI_ONLY%"=="1" (
    if not defined CDS_GUI_EXE (
        echo Error: CDS GUI executable not found
        echo Please check CDS tool path: %CDS_TOOL_PATH%
        exit /b 1
    )
    echo Launching CDS GUI only...
    start "" "%CDS_GUI_EXE%" -data "%WORKSPACE%"
    exit /b 0
)

echo Starting build via CDS tool...
echo Workspace: %WORKSPACE%
echo Java: %JAVA_EXE%
echo Launcher: %LAUNCHER_JAR%
echo.

if "%BUILD_CMD%"=="-cleanBuild" echo Clean build requested...

REM Build using Eclipse headless build
REM -nosplash: No splash screen
REM -application: Use headless build application (must come before -data to override perspective)
REM -data: Workspace location
REM -import: Import project (if not already imported)
REM -build or -cleanBuild: Build specific configuration
REM Note: Do not pass launcher-only args (e.g. --launcher.suppressErrors)
REM Note: Application must be specified before -data to avoid perspective parameter

REM Create log file in script directory
set "BUILD_LOG=%SCRIPT_DIR%build_lpac014_%RANDOM%.log"
if exist "%BUILD_LOG%" del "%BUILD_LOG%" >nul 2>&1

echo Executing build command...
if "%VERBOSE%"=="1" (
    set "VERBOSE_ARG=-verbose"
) else (
    set "VERBOSE_ARG="
)
if "%USE_CDS_EXE%"=="1" (
    REM Build using cds.exe with custom launcher.ini to avoid -perspective
    set "CDS_EXE=%CDS_TOOL_PATH%\cds.exe"
    if not exist "%CDS_EXE%" (
        set "CDS_EXE=%CDS_TOOL_PATH%\eclipse.exe"
    )
    if not exist "%CDS_EXE%" (
        echo Error: CDS executable not found under %CDS_TOOL_PATH%
        exit /b 1
    )

    REM Find launcher library directory
    set "LAUNCHER_LIB_DIR="
    for /f "delims=" %%I in ('dir /b /s "%CDS_TOOL_PATH%\plugins\org.eclipse.equinox.launcher.win32.win32.x86_64_*" 2^>nul') do (
        set "LAUNCHER_LIB_DIR=%%I"
        goto :found_launcher_lib
    )
    :found_launcher_lib
    if not defined LAUNCHER_LIB_DIR (
        echo Error: Eclipse launcher library not found under %CDS_TOOL_PATH%\plugins
        exit /b 1
    )

    REM Build a minimal launcher.ini without -perspective
    set "LAUNCHER_INI=%SCRIPT_DIR%cds_headless.ini"
    (
        echo -startup
        echo %LAUNCHER_JAR%
        echo --launcher.library
        echo %LAUNCHER_LIB_DIR%
        echo -vm
        echo %JAVA_EXE%
        echo -vmargs
        echo -Dosgi.requiredJavaVersion=11
        echo -Xms40m
        echo -Xmx512m
    ) > "%LAUNCHER_INI%"

    echo Command: %CDS_EXE% -launcher.ini "%LAUNCHER_INI%" -application org.eclipse.cdt.managedbuilder.core.headlessbuild -nosplash -data "%WORKSPACE%" -import "%PROJECT_PATH%" %BUILD_CMD% "%PROJECT_NAME%/%BUILD_CONFIG%" %VERBOSE_ARG%
    echo.
    echo Build output will be logged to: %BUILD_LOG%
    echo Please wait, this may take a while...
    echo.

    REM Use /wait to avoid reading log while still writing
    start "" /wait "%CDS_EXE%" -launcher.ini "%LAUNCHER_INI%" -application org.eclipse.cdt.managedbuilder.core.headlessbuild -nosplash -data "%WORKSPACE%" -import "%PROJECT_PATH%" %BUILD_CMD% "%PROJECT_NAME%/%BUILD_CONFIG%" %VERBOSE_ARG% > "%BUILD_LOG%" 2>&1
) else (
    echo Command: %JAVA_EXE% -jar "%LAUNCHER_JAR%" -application org.eclipse.cdt.managedbuilder.core.headlessbuild -nosplash -data "%WORKSPACE%" -import "%PROJECT_PATH%" %BUILD_CMD% "%PROJECT_NAME%/%BUILD_CONFIG%" %VERBOSE_ARG%
    echo.
    echo Build output will be logged to: %BUILD_LOG%
    echo Please wait, this may take a while...
    echo.

    REM Execute build using Java directly to bypass eclipse.ini
    REM -verbose: Show detailed progress
    REM Redirect both stdout and stderr to log file and console
    "%JAVA_EXE%" -jar "%LAUNCHER_JAR%" -application org.eclipse.cdt.managedbuilder.core.headlessbuild -nosplash -data "%WORKSPACE%" -import "%PROJECT_PATH%" %BUILD_CMD% "%PROJECT_NAME%/%BUILD_CONFIG%" %VERBOSE_ARG% > "%BUILD_LOG%" 2>&1
)

set BUILD_EXIT_CODE=%ERRORLEVEL%

REM Display build log (if unlocked)
echo.
echo ========================================
echo Build Output:
echo ========================================
type "%BUILD_LOG%" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo (log file is locked, please open it manually: %BUILD_LOG%)
) else (
    type "%BUILD_LOG%"
)
echo ========================================
echo.

REM Keep log file for inspection
if exist "%LAUNCHER_INI%" del "%LAUNCHER_INI%" >nul 2>&1

if %BUILD_EXIT_CODE% equ 0 (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    if "%DO_GUI%"=="1" (
        if defined CDS_GUI_EXE (
            echo Launching CDS GUI...
            start "" "%CDS_GUI_EXE%" -data "%WORKSPACE%"
        ) else (
            echo Warning: CDS GUI executable not found, skip launching UI.
        )
    )
    exit /b 0
) else (
    echo.
    echo ========================================
    echo Build failed with exit code: %BUILD_EXIT_CODE%
    echo ========================================
    exit /b %BUILD_EXIT_CODE%
)
