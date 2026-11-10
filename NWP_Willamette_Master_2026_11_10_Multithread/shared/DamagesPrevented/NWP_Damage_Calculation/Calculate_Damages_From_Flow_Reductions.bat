@echo off
setlocal

REM ===========================================
REM Configuration
REM ===========================================
set "ENV_NAME=USGS_CWMS_Download"
set "YML_FILE=%~dp0environment.yml"
set "PY_SCRIPT=%~dp0Calculate_DP.py"

echo ===========================================
echo  USGS_CWMS_Download Bootstrap + Runner
echo ===========================================
echo.

REM --- verify environment.yml exists ---
if not exist "%YML_FILE%" (
    echo [ERROR] environment.yml not found in:
    echo   %~dp0
    echo.
    pause
    exit /b 1
)

REM ===========================================
REM Conda install locations to check
REM ===========================================
set "CHECK1=%USERPROFILE%\Miniconda3"
set "CHECK2=%USERPROFILE%\Anaconda3"
set "CHECK3=%LOCALAPPDATA%\miniconda3"
set "CHECK4=%LOCALAPPDATA%\anaconda3"
set "CHECK5=C:\ProgramData\Miniconda3"
set "CHECK6=C:\ProgramData\Anaconda3"

echo [INFO] Searching for Conda in the following locations:
echo   1. %CHECK1%
echo   2. %CHECK2%
echo   3. %CHECK3%
echo   4. %CHECK4%
echo   5. %CHECK5%
echo   6. %CHECK6%
echo.

set "CONDA_DIR="

REM Check each location and report result
for %%C in ("%CHECK1%" "%CHECK2%" "%CHECK3%" "%CHECK4%" "%CHECK5%" "%CHECK6%") do (
    if exist "%%~C\Scripts\activate.bat" (
        echo [FOUND]  %%~C
        if "%CONDA_DIR%"=="" set "CONDA_DIR=%%~C"
    ) else (
        echo [MISSING] %%~C
    )
)

echo.

IF "%CONDA_DIR%"=="" (
    echo [ERROR] No Conda installation found in any of the checked paths.
    echo Please install Miniconda:
    echo   https://docs.conda.io/en/latest/miniconda.html
    echo.
    pause
    exit /b 1
)

echo [INFO] Using Conda found at:
echo   %CONDA_DIR%
echo.

REM ===========================================
REM Activate base Conda
REM ===========================================
call "%CONDA_DIR%\Scripts\activate.bat"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate base Conda.
    echo.
    pause
    exit /b 1
)

REM ===========================================
REM Check if environment exists
REM ===========================================
echo [INFO] Checking for environment "%ENV_NAME%"...
conda env list | findstr /I " %ENV_NAME% " >nul 2>&1
if %ERRORLEVEL% EQU 0 goto EnvExists

echo [INFO] Environment not found.
echo [INFO] Creating it from environment.yml...
echo.

conda env create -f "%YML_FILE%"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create environment.
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Environment created successfully.

:EnvExists
echo.
echo [INFO] Activating environment "%ENV_NAME%"...
call conda activate %ENV_NAME%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate environment.
    echo.
    pause
    exit /b 1
)

REM ===========================================
REM Run your Python script
REM ===========================================
echo.
echo [INFO] Running Calculate_DP.py ...
echo -------------------------------------------
python "%PY_SCRIPT%"
echo -------------------------------------------

echo.
echo [SUCCESS] Script completed.
pause
exit /b 0
