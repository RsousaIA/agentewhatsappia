# Agente de Suporte WhatsApp

Sistema de automação para atendimento e análise de conversas do WhatsApp, com funcionalidades de coleta, processamento e avaliação de mensagens.

## Estrutura do Projeto

```
├── agent/
│   ├── collector_agent.py     # Agente responsável pela coleta e processamento de mensagens
│   ├── evaluator_agent.py     # Agente responsável pela avaliação de conversas
│   ├── ollama_integration.py  # Integração com modelo de linguagem Ollama
│   ├── evaluation_manager.py  # Gerenciador de avaliações
│   ├── conversation_processor.py # Processador de conversas
│   └── prompts_library.py     # Biblioteca de prompts para o modelo
├── database/
│   ├── firebase_db.py         # Cliente para interação com Firebase
│   └── models/                # Modelos de dados do sistema
├── logs/                      # Diretório de logs
├── .env                       # Arquivo de variáveis de ambiente
├── main.py                    # Ponto de entrada principal da aplicação
└── requirements.txt           # Dependências do projeto
```

## Funcionalidades

- **Integração com WhatsApp**: Envio e recebimento de mensagens via WhatsApp.
- **Agente Coletor**: 
  - Processa mensagens recebidas
  - Analisa conteúdo usando modelo de linguagem
  - Gerencia conversas ativas
  - Detecta solicitações e reclamações
  - Gerencia encerramento de conversas
- **Agente Avaliador**: 
  - Avalia conversas encerradas
  - Gera métricas de qualidade
  - Calcula NPS
  - Identifica pontos de melhoria
  - Consolida métricas de atendimento
- **Integração com Ollama**: 
  - Análise de mensagens
  - Detecção de intenções
  - Avaliação de conversas
  - Geração de resumos
- **Armazenamento Firebase**: Persistência de dados de conversas e mensagens.

## Requisitos

- Python 3.8+
- Node.js 14+ (para whatsapp-web.js)
- Conta no Firebase (Firestore)
- Acesso à API do WhatsApp
- Servidor Ollama (opcional, pode usar modo simulação)

## Configuração

1. Clone o repositório
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Configure o arquivo `.env` com as seguintes variáveis:
   ```
   # Firebase
   FIREBASE_CREDENTIALS=path/to/credentials.json
   
   # WhatsApp
   WHATSAPP_SESSION_PATH=./whatsapp-session
   
   # Ollama
   OLLAMA_URL=http://localhost:11434
   OLLAMA_MODEL=mistral
   OLLAMA_SIMULATION_MODE=false
   
   # Configurações de Agentes
   INACTIVITY_TIMEOUT=3600
   EVALUATION_INTERVAL=3600
   CLEANUP_INTERVAL=1800
   VERIFICATION_INTERVAL_MINUTES=10
   
   # Logging
   LOG_LEVEL=INFO
   ```

4. Execute a aplicação:
   ```
   python main.py
   ```

## Componentes Principais

### Agente Coletor

- Processa mensagens recebidas
- Cria e gerencia conversas
- Analisa conteúdo das mensagens
- Detecta solicitações e reclamações
- Gerencia encerramento de conversas

### Agente Avaliador

- Avalia conversas encerradas
- Calcula métricas de qualidade
- Gera NPS
- Identifica pontos de melhoria
- Consolida métricas de atendimento

### Integração Ollama

- Análise de mensagens
- Detecção de intenções
- Avaliação de conversas
- Geração de resumos

### Firebase Database

- Armazena dados de conversas
- Persiste mensagens
- Mantém histórico de avaliações
- Armazena métricas consolidadas

## Licença

Este projeto está licenciado sob a licença MIT. 