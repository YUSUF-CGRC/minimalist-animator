@echo off
rem Minimalist Animator komut satiri: ma <arac> [argumanlar]   (liste: ma yardim)
rem Yorumlayici sirasi: <proje koku>\sirket\.python -> python3 -> python -> py -3
setlocal
set "MA_BETIK=%~dp0..\studyo\ma.py"
set "MA_PY="
if defined MA_KOK if exist "%MA_KOK%\sirket\.python" set /p MA_PY=<"%MA_KOK%\sirket\.python"
if not defined MA_PY if defined CLAUDE_PROJECT_DIR if exist "%CLAUDE_PROJECT_DIR%\sirket\.python" set /p MA_PY=<"%CLAUDE_PROJECT_DIR%\sirket\.python"
if not defined MA_PY if exist "%CD%\sirket\.python" set /p MA_PY=<"%CD%\sirket\.python"
if defined MA_PY (
  "%MA_PY%" -c "import sys" >nul 2>&1
  if not errorlevel 1 goto :ozel
)
python3 -c "import sys" >nul 2>&1
if not errorlevel 1 goto :python3
python -c "import sys" >nul 2>&1
if not errorlevel 1 goto :python
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 goto :py
echo ma: Python 3 bulunamadi. Python 3.10+ kurun ya da sirket\.python dosyasina yorumlayicinin yolunu yazin. 1>&2
exit /b 127
:ozel
"%MA_PY%" "%MA_BETIK%" %*
exit /b %errorlevel%
:python3
python3 "%MA_BETIK%" %*
exit /b %errorlevel%
:python
python "%MA_BETIK%" %*
exit /b %errorlevel%
:py
py -3 "%MA_BETIK%" %*
exit /b %errorlevel%
