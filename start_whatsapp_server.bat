@echo off
echo ============================================
echo    SERVIDOR WHATSAPP - INICIADOR
echo ============================================
echo.

:: Verifica se o Node.js está instalado
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Node.js nao encontrado. Por favor, instale o Node.js antes de continuar.
    pause
    exit /b 1
)

:: Cria diretório de logs se não existir
if not exist "logs" mkdir logs

:: Instala dependências do Node.js
echo [1/2] Instalando dependencias do Node.js...
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Falha ao instalar dependencias do Node.js.
    pause
    exit /b 1
)

:: Inicia o servidor Node.js
echo [2/2] Iniciando servidor WhatsApp...
node whatsapp_server.js

:: Se o servidor fechar, mostra mensagem
echo Servidor encerrado.
pause 