@echo off
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Python 3 nao encontrado. Instale Python 3.10+ e tente de novo.
  pause
  exit /b 1
)

call :health
if not errorlevel 1 goto open

echo O servidor em 8768 nao respondeu. Encerrando copias antigas...
powershell -NoProfile -Command "$procs = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*expense_server.py*' }); foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }"
powershell -NoProfile -Command "Start-Sleep -Seconds 1" >nul

echo Iniciando servidor my-home...
start "my-home expenses" /D "%~dp0" %PY% "%~dp0python\expense_server.py"

set "READY="
for /L %%I in (1,1,20) do (
  if not defined READY (
    powershell -NoProfile -Command "Start-Sleep -Seconds 1" >nul
    call :health
    if not errorlevel 1 set "READY=1"
  )
)
if not defined READY (
  echo.
  echo Falha ao iniciar o servidor em http://127.0.0.1:8768/
  echo Veja a janela "my-home expenses" para o erro.
  echo.
  pause
  exit /b 1
)

:open
start "" "http://127.0.0.1:8768/"
endlocal
exit /b 0

:health
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8768/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
exit /b %errorlevel%
