@echo on
setlocal enableextensions disabledelayedexpansion

start "" %PYTHON%\\Scripts\\tox.exe -e py -- -m unit -n 8
call :timeoutProcess "%PYTHON%\\Scripts\\tox.exe" 300

exit /b

:timeoutProcess process timeout [leave]
    rem process = name of process to monitor
    rem timeout = timeout in seconds to wait for process to end
    rem leave   = 1 if process should not be killed on timeout
    for /l %%t in (1 1 %~2) do (
        timeout /t 1 >nul
        tasklist | find /i "%~1" >nul || exit /b 0
    )
    if not "%~3"=="1" taskkill /f /im "%~1" >nul 2>nul
    if %errorlevel% equ 128 ( exit /b 0 ) else ( exit /b 1 )
