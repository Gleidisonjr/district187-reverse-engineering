@echo off
setlocal
cd /d "%~dp0"

set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
if not exist "%VCVARS%" (
    echo [ERRO] MSVC 2019 Build Tools x86 nao encontrado em: %VCVARS%
    exit /b 1
)

call "%VCVARS%" >nul
echo [*] Compilando D187_ServerHost.exe (x86)...
cl /nologo /EHsc /O2 /Fe:D187_ServerHost.exe d187_server_host.cpp /Fo:d187_server_host.obj
if %errorlevel% neq 0 (
    echo [ERRO] Falha na compilacao!
    exit /b %errorlevel%
)
del /q d187_server_host.obj 2>nul
echo [+] D187_ServerHost.exe compilado com sucesso!
