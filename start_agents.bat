@echo off
title AGENTES DE ANÁLISE - INICIADOR

echo Verificando Python...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python nao encontrado! Por favor, instale o Python 3.8 ou superior.
    pause
    exit /b 1
)

echo Criando diretorio de logs...
if not exist logs mkdir logs

echo Verificando configuracoes do Firebase...

:: Verifica se o arquivo de credenciais existe
if exist "D:\Projetos Python\AgenteSuporteWhatsapp\agentewhatsappv1-firebase-adminsdk-fbsvc-54b4b70f96.json" (
    echo Arquivo de credenciais do Firebase encontrado.
    goto :install_deps
)

echo Arquivo de credenciais do Firebase nao encontrado!
echo Verificando configuracoes no .env...

:: Verifica se o .env existe
if not exist .env (
    echo Arquivo .env nao encontrado! Criando arquivo de exemplo...
    echo # Configuracoes do Firebase> .env
    echo FIREBASE_PROJECT_ID=agentewhatsappv1>> .env
    echo FIREBASE_PRIVATE_KEY=seu-private-key>> .env
    echo FIREBASE_CLIENT_EMAIL=seu-client-email>> .env
    echo FIREBASE_API_KEY=AIzaSyCgTtAaI0F7kVC1x46FQF2r6xUMYslJxgs>> .env
    echo FIREBASE_AUTH_DOMAIN=agentewhatsappv1.firebaseapp.com>> .env
    echo FIREBASE_STORAGE_BUCKET=agentewhatsappv1.firebasestorage.app>> .env
    echo FIREBASE_MESSAGING_SENDER_ID=424267681639>> .env
    echo FIREBASE_APP_ID=1:424267681639:web:2dd3e6b80c3a50917629c2>> .env
    echo FIREBASE_DATABASE_URL=https://suainstancia.firebaseio.com>> .env
    echo FIREBASE_CREDENTIALS_PATH=D:\Projetos Python\AgenteSuporteWhatsapp\agentewhatsappv1-firebase-adminsdk-fbsvc-54b4b70f96.json>> .env
    echo.
    echo Por favor, configure o arquivo .env com suas credenciais do Firebase antes de continuar.
    pause
    exit /b 1
)

:: Verifica se as credenciais necessárias estão no .env
set CREDENTIALS_OK=1

:: Verifica FIREBASE_PRIVATE_KEY
findstr /C:"FIREBASE_PRIVATE_KEY=" .env >nul
if %ERRORLEVEL% neq 0 (
    echo Variavel FIREBASE_PRIVATE_KEY nao encontrada no .env!
    set CREDENTIALS_OK=0
)

:: Verifica FIREBASE_CLIENT_EMAIL
findstr /C:"FIREBASE_CLIENT_EMAIL=" .env >nul
if %ERRORLEVEL% neq 0 (
    echo Variavel FIREBASE_CLIENT_EMAIL nao encontrada no .env!
    set CREDENTIALS_OK=0
)

:: Verifica FIREBASE_DATABASE_URL
findstr /C:"FIREBASE_DATABASE_URL=" .env >nul
if %ERRORLEVEL% neq 0 (
    echo Variavel FIREBASE_DATABASE_URL nao encontrada no .env!
    set CREDENTIALS_OK=0
)

if %CREDENTIALS_OK% equ 0 (
    echo Por favor, configure todas as credenciais necessarias no arquivo .env
    pause
    exit /b 1
)

echo Credenciais do Firebase configuradas no .env

:install_deps
echo Instalando dependencias...
call pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Erro ao instalar dependencias!
    pause
    exit /b 1
)

echo Iniciando agentes de analise...
python new_main.py

echo.
echo Agentes encerrados.
pause 