@echo off
echo Executando testes...

REM Criar diretório para relatórios se não existir
if not exist "reports" mkdir reports

REM Obter data e hora para nome do arquivo
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set datetime=%%a
set year=%datetime:~0,4%
set month=%datetime:~4,2%
set day=%datetime:~6,2%
set hour=%datetime:~8,2%
set minute=%datetime:~10,2%
set second=%datetime:~12,2%

set timestamp=%year%%month%%day%_%hour%%minute%%second%
set report_file=reports\test_report_%timestamp%.txt

REM Executar testes
echo Executando testes...
python -m pytest tests -v > %report_file% 2>&1

REM Verificar resultado
echo.
echo Resultados dos testes:
type %report_file%

REM Verificar se os testes passaram
findstr "failed" %report_file% >nul
if %errorlevel% equ 0 (
    echo ❌ Alguns testes falharam.
) else (
    echo ✅ Todos os testes passaram com sucesso!
)

echo.
echo Relatório salvo em: %report_file%
echo. 