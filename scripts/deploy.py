import os
import sys
import subprocess
from setup_env import check_python_path, check_dependencies

def run_tests():
    """Executa os testes antes do deploy."""
    print("🧪 Executando testes...")
    test_result = subprocess.run(
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
        capture_output=True,
        text=True
    )
    
    if test_result.returncode != 0:
        print("❌ Falha nos testes:")
        print(test_result.stdout)
        print(test_result.stderr)
        return False
        
    print("✅ Testes passaram com sucesso!")
    return True

def check_env_vars():
    """Verifica se todas as variáveis de ambiente necessárias estão configuradas."""
    required_vars = [
        'FIREBASE_CREDENTIALS',
        'WHATSAPP_API_KEY',
        'OLLAMA_HOST'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Variáveis de ambiente faltando:")
        for var in missing_vars:
            print(f"  - {var}")
        return False
        
    print("✅ Todas as variáveis de ambiente estão configuradas")
    return True

def update_requirements():
    """Atualiza o arquivo requirements.txt com as dependências atuais."""
    print("📦 Atualizando requirements.txt...")
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'freeze'],
            stdout=open('requirements.txt', 'w'),
            check=True
        )
        print("✅ requirements.txt atualizado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao atualizar requirements.txt: {str(e)}")
        return False

def main():
    """Função principal do script de deploy."""
    print("🚀 Iniciando processo de deploy...")
    
    # Verifica ambiente
    if not check_python_path():
        print("❌ PYTHONPATH não está configurado corretamente")
        return
        
    if not check_dependencies():
        print("❌ Dependências não estão instaladas corretamente")
        return
        
    if not check_env_vars():
        print("❌ Variáveis de ambiente não estão configuradas corretamente")
        return
        
    # Atualiza requirements.txt
    if not update_requirements():
        print("❌ Falha ao atualizar requirements.txt")
        return
        
    # Executa testes
    if not run_tests():
        print("❌ Falha nos testes - Deploy cancelado")
        return
    
    print("\n✨ Deploy concluído com sucesso!")
    print("\nPróximos passos:")
    print("1. Verifique os logs do sistema")
    print("2. Monitore as métricas iniciais")
    print("3. Teste as funcionalidades principais")

if __name__ == '__main__':
    main() 