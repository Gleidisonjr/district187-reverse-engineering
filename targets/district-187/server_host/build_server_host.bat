@echo off
setlocal
cd /d "%~dp0"

set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
if not exist "%VCVARS%" goto :no_vc

call "%VCVARS%" >nul
echo [*] Compilando D187_ServerHost.exe (x86)...
cl /nologo /EHsc /O2 /Fe:D187_ServerHost.exe d187_server_host.cpp /Fo:d187_server_host.obj
if errorlevel 1 goto :build_fail
del /q d187_server_host.obj 2>nul
echo [+] D187_ServerHost.exe compilado com sucesso!
exit /b 0

:no_vc
echo [ERRO] MSVC 2019 Build Tools x86 nao encontrado.
exit /b 1

:build_fail
echo [ERRO] Falha na compilacao!
exit /b 1
