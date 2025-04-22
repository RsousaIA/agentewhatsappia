# Documentação da API

## Visão Geral

Esta documentação descreve a API do Sistema de Atendimento WhatsApp. A API é RESTful e utiliza JSON para troca de dados.

### Autenticação

Todas as requisições devem incluir um token JWT no header:

```
Authorization: Bearer <token>
```

### Endpoints Base

- Produção: `https://api.seusistema.com/v1`
- Desenvolvimento: `https://dev-api.seusistema.com/v1`

## Endpoints

### Conversas

#### Listar Conversas
```
GET /conversations
```

Parâmetros de Query:
- `status` (opcional): Filtro por status (em_andamento, encerrada, reaberta)
- `startDate` (opcional): Data inicial
- `endDate` (opcional): Data final
- `page` (opcional): Número da página
- `limit` (opcional): Itens por página

Resposta:
```json
{
  "data": [
    {
      "id": "string",
      "client": "string",
      "status": "string",
      "startDate": "string",
      "lastMessage": "string",
      "attendants": ["string"]
    }
  ],
  "pagination": {
    "total": "number",
    "page": "number",
    "limit": "number"
  }
}
```

#### Obter Detalhes da Conversa
```
GET /conversations/{id}
```

Resposta:
```json
{
  "id": "string",
  "client": "string",
  "status": "string",
  "startDate": "string",
  "endDate": "string",
  "messages": [
    {
      "id": "string",
      "content": "string",
      "sender": "string",
      "timestamp": "string"
    }
  ],
  "requests": [
    {
      "id": "string",
      "description": "string",
      "deadline": "string",
      "status": "string"
    }
  ]
}
```

### Avaliações

#### Listar Avaliações
```
GET /evaluations
```

Parâmetros de Query:
- `conversationId` (opcional): ID da conversa
- `startDate` (opcional): Data inicial
- `endDate` (opcional): Data final
- `page` (opcional): Número da página
- `limit` (opcional): Itens por página

Resposta:
```json
{
  "data": [
    {
      "id": "string",
      "conversationId": "string",
      "scores": {
        "communication": "number",
        "technicalKnowledge": "number",
        "empathy": "number",
        "professionalism": "number",
        "results": "number",
        "emotionalIntelligence": "number",
        "deadlines": "number"
      },
      "finalScore": "number",
      "comments": "string"
    }
  ],
  "pagination": {
    "total": "number",
    "page": "number",
    "limit": "number"
  }
}
```

### Relatórios

#### Gerar Relatório
```
POST /reports
```

Corpo da Requisição:
```json
{
  "type": "string", // daily, weekly, monthly
  "startDate": "string",
  "endDate": "string",
  "format": "string" // pdf, excel
}
```

Resposta:
```json
{
  "id": "string",
  "status": "string",
  "url": "string"
}
```

## Webhooks

### Eventos Disponíveis

1. **Nova Mensagem**
   - URL: `/webhooks/new-message`
   - Método: POST
   - Corpo:
   ```json
   {
     "conversationId": "string",
     "messageId": "string",
     "content": "string",
     "sender": "string",
     "timestamp": "string"
   }
   ```

2. **Conversa Encerrada**
   - URL: `/webhooks/conversation-closed`
   - Método: POST
   - Corpo:
   ```json
   {
     "conversationId": "string",
     "endDate": "string",
     "reason": "string"
   }
   ```

3. **Nova Avaliação**
   - URL: `/webhooks/new-evaluation`
   - Método: POST
   - Corpo:
   ```json
   {
     "conversationId": "string",
     "evaluationId": "string",
     "scores": {
       "communication": "number",
       "technicalKnowledge": "number",
       "empathy": "number",
       "professionalism": "number",
       "results": "number",
       "emotionalIntelligence": "number",
       "deadlines": "number"
     },
     "finalScore": "number"
   }
   ```

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 400 | Requisição inválida |
| 401 | Não autorizado |
| 403 | Acesso negado |
| 404 | Recurso não encontrado |
| 429 | Muitas requisições |
| 500 | Erro interno do servidor |

## Limites de Requisição

- 100 requisições por minuto por IP
- 1000 requisições por hora por usuário
- 10000 requisições por dia por aplicação

## Exemplos

### Exemplo em Python

```python
import requests

BASE_URL = "https://api.seusistema.com/v1"
TOKEN = "seu-token-jwt"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Listar conversas
response = requests.get(
    f"{BASE_URL}/conversations",
    headers=headers,
    params={
        "status": "em_andamento",
        "page": 1,
        "limit": 10
    }
)

print(response.json())
```

### Exemplo em JavaScript

```javascript
const BASE_URL = "https://api.seusistema.com/v1";
const TOKEN = "seu-token-jwt";

const headers = {
  Authorization: `Bearer ${TOKEN}`,
  "Content-Type": "application/json"
};

// Listar conversas
fetch(`${BASE_URL}/conversations?status=em_andamento&page=1&limit=10`, {
  headers
})
  .then(response => response.json())
  .then(data => console.log(data));
``` 