#!/usr/bin/env python3
"""
Script para executar os testes e gerar relatórios de cobertura.
"""
import os
import sys
import subprocess
from datetime import datetime

def run_tests():
    """Executa os testes e gera relatórios"""
    print("Iniciando execução dos testes...")
    
    # Criar diretório para relatórios se não existir
    if not os.path.exists("reports"):
        os.makedirs("reports")
    
    # Nome do arquivo de relatório com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"reports/test_report_{timestamp}.txt"
    coverage_file = f"reports/coverage_{timestamp}.html"
    
    try:
        # Executar testes com pytest
        cmd = [
            "pytest",
            "-v",
            "--cov=agent",
            "--cov=database",
            "--cov=utils",
            "--cov=whatsapp",
            "--cov-report=term-missing",
            f"--cov-report=html:{coverage_file}",
            "-n", "auto"  # Executar em paralelo
        ]
        
        print("Executando testes...")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Salvar relatório
        with open(report_file, "w") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\nErros:\n")
                f.write(result.stderr)
        
        # Exibir resultados
        print("\nResultados dos testes:")
        print(result.stdout)
        
        if result.stderr:
            print("\nErros encontrados:")
            print(result.stderr)
        
        # Verificar resultado
        if result.returncode == 0:
            print("\n✅ Todos os testes passaram com sucesso!")
        else:
            print("\n❌ Alguns testes falharam.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Erro ao executar testes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests() 