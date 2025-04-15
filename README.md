# Agente de Suporte WhatsApp

Sistema automatizado para gerenciamento e avaliação de conversas do WhatsApp Business.

## Requisitos

- Python 3.11+
- Node.js 16+
- MySQL 8.0+ (opcional, pode usar SQLite para desenvolvimento)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/agente-suporte-whatsapp.git
cd agente-suporte-whatsapp
```

2. Crie e ative o ambiente virtual Python:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências Python:
```bash
pip install -r requirements.txt
```

4. Instale as dependências Node.js:
```bash
cd node
npm install
```

5. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## Configuração

1. Configure o banco de dados:
```bash
# Para SQLite (desenvolvimento)
python -m database.db_setup

# Para MySQL (produção)
# Configure o DATABASE_URL no .env e execute:
python -m database.db_setup
```

2. Configure o WhatsApp:
- Execute o servidor Node.js:
```bash
cd node
npm start
```
- Escaneie o QR code exibido no terminal
- Aguarde a mensagem "Cliente conectado!"

## Uso

1. Inicie o servidor Python:
```bash
python -m app
```

2. Os agentes serão iniciados automaticamente:
- Collector Agent: Coleta e processa mensagens
- Evaluator Agent: Avalia conversas e gera métricas
- Priority Manager: Gerencia prioridades de atendimento

## Estrutura do Projeto

```
.
├── agent/                 # Agentes do sistema
├── database/             # Configuração e modelos do banco
├── node/                 # Integração com WhatsApp
├── tests/               # Testes automatizados
├── utils/               # Funções utilitárias
├── .env.example         # Exemplo de variáveis de ambiente
├── requirements.txt     # Dependências Python
└── README.md           # Este arquivo
```

## Testes

Execute os testes com:
```bash
pytest
```

Para ver o relatório de cobertura:
```bash
pytest --cov
```

## Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes. 