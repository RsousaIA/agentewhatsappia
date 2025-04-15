@echo off
echo ============================================
echo    Agente de Suporte WhatsApp - Iniciador
echo ============================================
echo.

REM Verifica se Python 3.11 está instalado
py -3.11 --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3.11 não encontrado!
    echo Por favor, instale o Python 3.11 em: https://www.python.org/downloads/release/python-3116/
    pause
    exit /b 1
)

REM Verifica se o ambiente virtual existe
if not exist venv (
    echo 📦 Criando ambiente virtual Python...
    py -3.11 -m venv venv
) else (
    echo ✅ Ambiente virtual já existe
)

REM Ativa o ambiente virtual e instala/atualiza dependências
echo 📦 Ativando ambiente virtual e instalando dependências...
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erro durante a instalação das dependências Python!
    pause
    exit /b 1
)

REM Verifica se node_modules existe
if not exist node_modules (
    echo 📦 Instalando dependências Node.js...
    call npm install
    if errorlevel 1 (
        echo ❌ Erro durante a instalação das dependências Node.js!
        pause
        exit /b 1
    )
)

REM Inicializa o banco de dados
echo 🗄️ Inicializando banco de dados...
python -c "from database.db import init_db; init_db()"
if errorlevel 1 (
    echo ❌ Erro durante a inicialização do banco de dados!
    pause
    exit /b 1
)

REM Inicia o servidor Node.js WhatsApp em segundo plano
echo 📱 Iniciando servidor WhatsApp em segundo plano...
start "Servidor WhatsApp" cmd /c "node whatsapp/node_client.js"
echo ✅ Servidor WhatsApp iniciado! Aguarde a exibição do QR Code.
echo ⏳ Aguardando 5 segundos para o servidor iniciar completamente...
timeout /t 5 /nobreak > nul

REM Inicia o sistema
echo 🚀 Iniciando sistema...
call node start.js

pause 