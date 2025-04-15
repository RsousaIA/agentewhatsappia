# Servidor de Integração WhatsApp

Este é o servidor Node.js responsável pela integração com o WhatsApp Web utilizando a biblioteca `whatsapp-web.js`.

## Estrutura do Projeto

```
node/
├── server.js          # Servidor principal
├── config.js          # Configurações
├── logger.js          # Sistema de logging
├── utils/             # Utilitários
│   └── phone.js       # Validação de números
├── tests/             # Testes
│   └── phone.test.js  # Testes de validação
└── logs/              # Logs da aplicação
```

## Requisitos

- Node.js 14.x ou superior
- NPM 6.x ou superior
- Python 3.8+ (para o backend)

## Instalação

1. Clone o repositório
2. Instale as dependências:
   ```bash
   npm install
   ```
3. Copie o arquivo `.env.example` para `.env` e configure as variáveis:
   ```bash
   cp .env.example .env
   ```
4. Inicie o servidor:
   ```bash
   npm start
   ```

## Uso

O servidor expõe as seguintes funcionalidades via Socket.IO:

### Eventos Recebidos

- `send_message`: Envia uma mensagem para um número
  ```javascript
  {
    to: "11999999999",  // Número do destinatário
    message: "Olá!"     // Mensagem a ser enviada
  }
  ```

### Eventos Emitidos

- `qr`: QR Code para autenticação
- `ready`: Cliente WhatsApp conectado
- `message`: Nova mensagem recebida
- `message_sent`: Mensagem enviada com sucesso
- `error`: Erro ao enviar mensagem
- `disconnected`: Cliente WhatsApp desconectado

## API

### Validação de Números

O servidor inclui funções para validação e formatação de números de telefone:

```javascript
const { formatPhoneNumber, isValidWhatsAppNumber } = require('./utils/phone');

// Formata um número para o padrão do WhatsApp
const formatted = formatPhoneNumber('11999999999');
// Retorna: "5511999999999@c.us"

// Valida se um número está no formato correto
const isValid = isValidWhatsAppNumber('5511999999999@c.us');
// Retorna: true
```

## Logs

Os logs são armazenados no diretório `logs/` e incluem:

- Informações de conexão
- Erros de validação
- Mensagens enviadas/recebidas
- Eventos do Socket.IO

## Segurança

- Validação de números de telefone
- CORS configurável
- Logs detalhados
- Tratamento de erros

## Troubleshooting

### Problemas Comuns

1. **QR Code não aparece**
   - Verifique se o Chrome está instalado
   - Limpe o cache do WhatsApp Web

2. **Erro ao enviar mensagem**
   - Verifique o formato do número
   - Confira se o destinatário está no WhatsApp

3. **Conexão perdida**
   - Verifique a conexão com a internet
   - Reinicie o servidor

### Logs

Os logs podem ser encontrados em:
- Console (durante o desenvolvimento)
- Arquivo de log (em produção)

Para mais informações, consulte a documentação do [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js). 