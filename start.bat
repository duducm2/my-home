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

REM Start server in a new console if not already healthy
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8768/health' -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo Iniciando servidor my-home...
  start "my-home expenses" %PY% "%~dp0python\expense_server.py"
  set "READY="
  for /L %%I in (1,1,15) do (
    if not defined READY (
      timeout /t 1 /nobreak >nul
      powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8768/health' -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
      if not errorlevel 1 set "READY=1"
    )
  )
  if not defined READY (
    echo.
    echo Falha ao iniciar o servidor em http://127.0.0.1:8768/
    echo Veja a janela "my-home expenses" para o erro ^(ex.: tasks.json invalido^).
    echo.
    pause
    exit /b 1
  )
)

start "" "http://127.0.0.1:8768/"
endlocal
