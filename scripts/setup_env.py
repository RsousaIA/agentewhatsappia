import os
import sys
import subprocess
import platform

def check_python_path():
    """Verifica se o PYTHONPATH está configurado corretamente."""
    current_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    python_path = os.environ.get('PYTHONPATH', '')
    
    if current_path not in python_path:
        print(f"❌ PYTHONPATH não está configurado corretamente.")
        print(f"Atual: {python_path}")
        print(f"Esperado: {current_path}")
        return False
    return True

def setup_python_path():
    """Configura o PYTHONPATH."""
    current_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    if platform.system() == 'Windows':
        # PowerShell
        cmd = f'$env:PYTHONPATH = "{current_path}"'
        print("\nPara PowerShell, execute:")
        print(cmd)
        
        # CMD
        cmd = f'set PYTHONPATH={current_path}'
        print("\nPara CMD, execute:")
        print(cmd)
    else:
        # Linux/Mac
        cmd = f'export PYTHONPATH={current_path}'
        print("\nPara Linux/Mac, execute:")
        print(cmd)
        
        # Adiciona ao .bashrc ou .zshrc
        shell = os.environ.get('SHELL', '').lower()
        if 'zsh' in shell:
            rc_file = os.path.expanduser('~/.zshrc')
        else:
            rc_file = os.path.expanduser('~/.bashrc')
            
        print(f"\nPara adicionar permanentemente, adicione a linha abaixo ao {rc_file}:")
        print(cmd)

def check_dependencies():
    """Verifica se todas as dependências estão instaladas."""
    try:
        import firebase_admin
        import flask
        import ollama
        print("✅ Todas as dependências principais estão instaladas.")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {str(e)}")
        print("Execute: pip install -r requirements.txt")
        return False

def main():
    """Função principal para verificar e configurar o ambiente."""
    print("🔍 Verificando ambiente...")
    
    # Verifica Python
    python_version = sys.version_info
    print(f"\nPython versão: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python 3.8+ é necessário")
        return
    
    # Verifica PYTHONPATH
    if not check_python_path():
        print("\n📝 Instruções para configurar PYTHONPATH:")
        setup_python_path()
    else:
        print("✅ PYTHONPATH está configurado corretamente")
    
    # Verifica dependências
    print("\n📦 Verificando dependências...")
    check_dependencies()
    
    print("\n✨ Configuração concluída!")

if __name__ == '__main__':
    main() 