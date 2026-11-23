@echo off
cd /d "%~dp0"
if not exist "node_modules\@electric-sql\pglite\package.json" (
  echo Instalando a dependencia do banco local...
  call npm install
  if errorlevel 1 (
    echo Falha na instalacao. Verifique Node.js e a conexao.
    pause
    exit /b 1
  )
)
echo.
echo CONFIA: abra http://127.0.0.1:3000 no navegador.
echo Mantenha esta janela aberta durante a demonstracao.
echo.
call npm start
pause
