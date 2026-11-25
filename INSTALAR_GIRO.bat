@echo off
setlocal EnableExtensions
title GIRO - instalar projeto e dependencias

set "PROJECT=%~dp0"
set "CHECK_ONLY=0"
if /I "%~1"=="--check" set "CHECK_ONLY=1"

echo.
echo ==========================================
echo   GIRO - preparacao para a apresentacao
echo ==========================================
echo.

if not exist "%PROJECT%requirements.txt" (
    if "%CHECK_ONLY%"=="1" (
        echo Projeto ainda nao foi baixado nesta pasta.
        exit /b 1
    )
    if exist "%~dp0Projeto_A3_Bigdata-main\requirements.txt" (
        set "PROJECT=%~dp0Projeto_A3_Bigdata-main\"
    ) else (
        if exist "%~dp0Projeto_A3_Bigdata-main" (
            echo Pasta Projeto_A3_Bigdata-main ja existe, mas parece incompleta. Confira antes de repetir.
            goto :fail
        )
        echo Baixando o projeto da conta GuilhermeDosSantosSantana...
        set "GIRO_DOWNLOAD_DIR=%~dp0"
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $zip=Join-Path $env:TEMP 'Projeto_A3_Bigdata-main.zip'; Invoke-WebRequest -Uri 'https://github.com/GuilhermeDosSantosSantana/Projeto_A3_Bigdata/archive/refs/heads/main.zip' -OutFile $zip; Expand-Archive -LiteralPath $zip -DestinationPath $env:GIRO_DOWNLOAD_DIR"
        if errorlevel 1 goto :fail
        set "PROJECT=%~dp0Projeto_A3_Bigdata-main\"
    )
)

if not exist "%PROJECT%requirements.txt" (
    echo Projeto incompleto: requirements.txt nao encontrado.
    goto :fail
)
if not exist "%PROJECT%entrega\GIRO_mysql_A3.sql.gz" (
    echo Backup do banco nao encontrado no projeto.
    goto :fail
)
echo Projeto: %PROJECT%

if "%CHECK_ONLY%"=="1" (
    if exist "%PROJECT%.venv\Scripts\python.exe" (echo Python virtual: OK) else (echo Python virtual: ausente)
    if exist "%ProgramFiles%\MySQL\MySQL Server 8.4\bin\mysql.exe" (echo MySQL 8.4: OK) else (echo MySQL 8.4: nao encontrado no caminho padrao)
    if exist "%PROJECT%mysql\runtime\app.cnf" (echo Acesso ao banco: configurado) else (echo Acesso ao banco: pendente)
    if exist "%PROJECT%.venv\Scripts\python.exe" (
        pushd "%PROJECT%"
        "%PROJECT%.venv\Scripts\python.exe" -m scripts.preparar_banco_equipe --check
        if errorlevel 1 (
            popd
            exit /b 1
        )
        popd
    )
    echo.
    echo Verificacao concluida; nenhuma instalacao foi iniciada.
    exit /b 0
)

where winget >nul 2>nul
if errorlevel 1 (
    echo O Gerenciador de Pacotes do Windows ^(winget^) nao esta disponivel.
    echo Instale o App Installer da Microsoft Store e rode este arquivo novamente.
    goto :fail
)

call :ensure_package Python.Python.3.13 "Python 3.13"
if errorlevel 1 goto :fail
call :ensure_package Microsoft.VCRedist.2015+.x64 "Visual C++ Runtime"
if errorlevel 1 goto :fail
call :ensure_package Oracle.MySQL "MySQL Server 8.4"
if errorlevel 1 goto :fail
call :ensure_package Oracle.MySQLWorkbench "MySQL Workbench"
if errorlevel 1 goto :fail

set "PYTHON_EXE="
for /f "delims=" %%P in ('py -3.13 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%ProgramFiles%\Python313\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python313\python.exe"
if not defined PYTHON_EXE (
    echo Python 3.13 foi instalado, mas ainda nao aparece nesta sessao.
    echo Feche esta janela e abra o .bat novamente.
    goto :fail
)

if not exist "%PROJECT%.venv\Scripts\python.exe" (
    echo Criando ambiente Python isolado...
    "%PYTHON_EXE%" -m venv "%PROJECT%.venv"
    if errorlevel 1 goto :fail
)
echo Instalando bibliotecas Python do projeto...
"%PROJECT%.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%PROJECT%requirements.txt"
if errorlevel 1 goto :fail

echo.
echo O MySQL precisa estar configurado e rodando. Se o Configurator abrir,
echo conclua a configuracao e guarde a senha root escolhida.
echo A senha sera solicitada pelo terminal sem aparecer na tela.
pushd "%PROJECT%"
"%PROJECT%.venv\Scripts\python.exe" -m scripts.preparar_banco_equipe
set "SETUP_EXIT=%ERRORLEVEL%"
popd
if not "%SETUP_EXIT%"=="0" (
    echo.
    echo Se o servidor MySQL ainda nao foi configurado, abra MySQL Configurator
    echo no menu Iniciar, configure a porta 3306 e rode este .bat novamente.
    goto :fail
)

echo.
echo Pronto. Abrindo o GIRO...
call "%PROJECT%INICIAR_GIRO.cmd"
exit /b %ERRORLEVEL%

:ensure_package
winget list --id %~1 --exact --source winget --accept-source-agreements 2>nul | findstr /i /c:"%~1" >nul
if not errorlevel 1 (
    echo %~2: instalado.
    exit /b 0
)
echo Instalando %~2 pelo winget...
winget install --id %~1 --exact --source winget --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo Falha ao instalar %~2.
    exit /b 1
)
exit /b 0

:fail
echo.
echo A preparacao nao terminou. Corrija a mensagem acima e rode o .bat novamente.
pause
exit /b 1
