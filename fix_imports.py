#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
from pathlib import Path

def fix_imports_in_file(file_path):
    """
    Corrige as importações em um arquivo, substituindo 'database' por 'database'
    e 'agent' por 'agent'.
    
    Args:
        file_path: Caminho para o arquivo a ser corrigido
    """
    print(f"Verificando arquivo: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Verificar se há importações a serem corrigidas
    if 'database' not in content and 'agent' not in content:
        print(f"  Nenhuma correção necessária")
        return
    
    # Substituir importações
    new_content = content.replace('database', 'database').replace('agent', 'agent')
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f"  Importações corrigidas")

def fix_imports_in_directory(directory):
    """
    Percorre todos os arquivos Python em um diretório recursivamente
    e corrige as importações.
    
    Args:
        directory: Diretório a ser percorrido
    """
    print(f"Verificando diretório: {directory}")
    
    python_files = list(Path(directory).rglob("*.py"))
    for file_path in python_files:
        fix_imports_in_file(file_path)

if __name__ == "__main__":
    # Diretório raiz do projeto
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Iniciando correção de importações...")
    print(f"Diretório raiz: {root_dir}")
    
    # Corrigir importações em todos os arquivos Python
    fix_imports_in_directory(root_dir)
    
    print("Correção de importações concluída!") 