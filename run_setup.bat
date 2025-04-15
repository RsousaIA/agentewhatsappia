@echo off
echo Configurando ambiente de testes...

REM Criar diretórios necessários
if not exist "tests" mkdir tests
if not exist "reports" mkdir reports

REM Verificar se pytest está instalado
pip show pytest >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando pytest...
    pip install pytest
)

REM Verificar se pytest-mock está instalado
pip show pytest-mock >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando pytest-mock...
    pip install pytest-mock
)

REM Verificar se os arquivos de teste existem
if not exist "tests\__init__.py" (
    echo Criando arquivo tests\__init__.py...
    echo. > tests\__init__.py
)

REM Verificar se o arquivo conftest.py existe
if not exist "tests\conftest.py" (
    echo Criando arquivo tests\conftest.py...
    (
        echo import pytest
        echo.
        echo @pytest.fixture
        echo def base_path^(^):
        echo     """Retorna o caminho base do projeto"""
        echo     import os
        echo     return os.path.dirname^(os.path.dirname^(os.path.abspath^(__file__^)^)^)
    ) > tests\conftest.py
)

echo.
echo Ambiente de testes configurado com sucesso!
echo Para executar os testes, execute: run_tests.bat
echo. 