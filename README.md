# 🤖 Zafitec AI Chat

> 💬 Um assistente conversacional inteligente em **Azure Functions** integrado com **Azure OpenAI (GPT-5)**

[![Deploy to Azure](https://img.shields.io/badge/Deploy-Azure_Functions-0078D4?logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/services/functions/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?logo=github-actions&logoColor=white)](.github/workflows/deploy.yml)
[![Status](https://img.shields.io/badge/Status-🟢_Em_Produção-success)]()

---

## ✨ Sobre o projeto

API serverless que expõe um endpoint HTTP de chat alimentado por **GPT-5-nano** via Azure OpenAI. Construída com Azure Functions em plano **Flex Consumption**, com pipeline de CI/CD totalmente automatizado pelo GitHub Actions.

Pensado para ser:

- 🚀 **Rápido** — respostas em ~3 segundos com `reasoning_effort=minimal`
- 💸 **Econômico** — Flex Consumption escala a zero quando ocioso
- 🔄 **Reproduzível** — `git push` faz o deploy completo
- 🛡️ **Resiliente** — tratamento granular de rate limits, falhas de conexão e erros de API
- 📊 **Observável** — logs estruturados via Application Insights

---

## 🏗️ Arquitetura

```
   👤 Cliente
      │
      │ POST /api/chat
      ▼
   ⚡ Azure Function (Python 3.10, Flex Consumption)
      │
      │ chat.completions.create()
      ▼
   🧠 Azure OpenAI - gpt-5-nano
      │
      ▼
   📝 Resposta em JSON
```

### 🔧 Stack

| Componente | Tecnologia |
|------------|------------|
| ⚙️ Runtime | Python 3.10 |
| 🌩️ Plano | Azure Functions Flex Consumption |
| 🤖 Modelo | Azure OpenAI — `gpt-5-nano` |
| 🔌 SDK | `openai==1.59.6` |
| 🚀 CI/CD | GitHub Actions |
| 📡 API Version | `2025-01-01-preview` |

---

## 📡 API

### `POST /api/chat`

Envia uma mensagem para o assistente e recebe a resposta.

#### 📥 Request

```json
{
  "message": "Como configurar uma VNet no Azure?"
}
```

#### 📤 Response (200 OK)

```json
{
  "response": "Para configurar uma VNet no Azure, você pode..."
}
```

#### ⚠️ Possíveis erros

| Status | Significado | Quando ocorre |
|--------|-------------|---------------|
| `400` | 🚫 Bad Request | Body inválido ou campo `message` ausente |
| `429` | 🐢 Too Many Requests | Rate limit do Azure OpenAI |
| `500` | 💥 Internal Error | Configuração do servidor incompleta ou erro inesperado |
| `502` | 🔌 Bad Gateway | Falha de conexão ou erro da API do OpenAI |

---

## 🚀 Como usar

### 🌐 Em produção

```powershell
$body = @{ message = "Olá, está funcionando?" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "https://zafitec-ai-chat.azurewebsites.net/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

### 🧪 Com `curl`

```bash
curl -X POST https://zafitec-ai-chat.azurewebsites.net/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Olá, está funcionando?"}'
```

### 📮 Com Postman / Insomnia

- **Method:** `POST`
- **URL:** `https://zafitec-ai-chat.azurewebsites.net/api/chat`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):** `{"message":"sua pergunta"}`

---

## 💻 Desenvolvimento local

### 📋 Pré-requisitos

- 🐍 [Python 3.10](https://www.python.org/downloads/release/python-31013/)
- 🛠️ [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- ☁️ [Azure CLI 2.55+](https://learn.microsoft.com/cli/azure/install-azure-cli)
- 📝 Editor (VS Code recomendado, com a extensão Azure Functions)

### ⚙️ Setup

**1. Clone o repositório:**

```powershell
git clone https://github.com/ErickMedeiros/zafitec-ai-chat.git
cd zafitec-ai-chat
```

**2. Crie e ative o virtualenv:**

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**3. Instale as dependências:**

```powershell
pip install -r requirements.txt
```

**4. Crie o `local.settings.json`** (não vai pro Git por causa do `.gitignore`):

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_OPENAI_ENDPOINT": "https://<seu-recurso>.cognitiveservices.azure.com/",
    "AZURE_OPENAI_API_KEY": "<sua-chave>",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-5-nano",
    "AZURE_OPENAI_API_VERSION": "2025-01-01-preview"
  },
  "Host": {
    "LocalHttpPort": 7071,
    "CORS": "*",
    "CORSCredentials": false
  }
}
```

**5. Rode localmente:**

```powershell
func start
```

**6. Teste:**

```powershell
$body = @{ message = "teste local" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:7071/api/chat" -Method POST -ContentType "application/json" -Body $body
```

✅ Pronto, está rodando em `http://localhost:7071/api/chat`.

---

## 🔄 Deploy

O deploy é **100% automatizado** via GitHub Actions. Para subir alterações:

```powershell
git add .
git commit -m "feat: sua mudança"
git push
```

⏱️ Em ~2 minutos a nova versão está em produção. Acompanhe no GitHub:
👉 [github.com/ErickMedeiros/zafitec-ai-chat/actions](https://github.com/ErickMedeiros/zafitec-ai-chat/actions)

### 🔐 Secrets necessários no GitHub

| Secret | Descrição |
|--------|-----------|
| `AZURE_CREDENTIALS` | JSON do Service Principal com role `Contributor` no Function App |

📖 Para detalhes de como criar o Service Principal e configurar do zero, veja o [**Guia de Configuração completo**](./guia-de-configuracao.md).

---

## 📁 Estrutura do projeto

```
zafitec-ai-chat/
├── 📂 .github/
│   └── 📂 workflows/
│       └── 🚀 deploy.yml              # Pipeline GitHub Actions
├── 🚫 .funcignore                     # Exclusões do empacotamento
├── 🚫 .gitignore                      # Exclusões do Git
├── 🐍 function_app.py                 # Código da Function
├── ⚙️ host.json                       # Config do host
├── 🔒 local.settings.json             # Config local (NÃO commitada)
├── 📖 README.md                       # Este arquivo
├── 📚 guia-de-configuracao.md         # Guia completo de deploy
└── 📦 requirements.txt                # Dependências Python
```

---

## 🧠 Configurações do GPT-5

Este projeto usa parâmetros otimizados para chat conversacional:

```python
completion = client.chat.completions.create(
    model=deployment,
    messages=[...],
    max_completion_tokens=4000,        # 📏 Margem ampla para reasoning + resposta
    reasoning_effort="minimal",        # ⚡ Mínimo raciocínio interno = resposta mais rápida
    # 🚫 Sem 'temperature' — GPT-5 só aceita default
    # 🚫 Sem 'max_tokens' — GPT-5 usa max_completion_tokens
)
```

### 🎚️ Níveis de `reasoning_effort`

| Nível | Quando usar |
|-------|-------------|
| `minimal` ⚡ | Chat geral, FAQ, traduções (este projeto) |
| `low` 🚶 | Tarefas com algum contexto |
| `medium` 🏃 | Equilíbrio padrão |
| `high` 🧗 | Matemática, código complexo, análise profunda |

📚 Detalhes completos no [Guia de Configuração](./guia-de-configuracao.md#15-particularidades-do-gpt-5).

---

## 📊 Monitoramento

### 📡 Logs em tempo real

No portal do Azure:

1. Acesse **Function App `zafitec-ai-chat`**
2. Menu lateral → **Monitoring → Log stream**

> ⚠️ **`az webapp log tail` NÃO funciona em Flex Consumption.** Use o portal ou Application Insights.

### 🔍 Application Insights

Métricas disponíveis automaticamente:

- 📈 Requests por minuto
- ⏱️ Latência (P50, P95, P99)
- 💥 Taxa de erros
- 🔢 Tokens consumidos (via logs `Usage`)

---

## 🐛 Troubleshooting

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| 🔴 `404` ao invocar `/api/chat` | Função não registrada após deploy | Aguarde 60s pós-deploy ou reinicie o app |
| 🟡 Resposta `200` mas `"response": ""` | Tokens consumidos no reasoning | Aumente `max_completion_tokens`, use `reasoning_effort="minimal"` |
| 🔴 `Client.__init__() got 'proxies'` | `openai` desatualizado | Atualize para `openai>=1.55` |
| 🐢 Primeira chamada demora 30-60s | Cold start do Flex | Comportamento esperado, próximas chamadas <5s |
| 🔴 Workflow falha em "Login no Azure" | Secret `AZURE_CREDENTIALS` inválido | Recrie o Service Principal e atualize o secret |

📖 Catálogo completo no [Guia de Configuração](./guia-de-configuracao.md#14-troubleshooting).

---

## 🗺️ Roadmap

Ideias para evoluir o projeto:

- [ ] 🔐 Adicionar autenticação (function keys ou Azure AD)
- [ ] 💭 Histórico de conversa (multi-turn)
- [ ] 🌊 Streaming de respostas (Server-Sent Events)
- [ ] 🎨 Frontend simples (React/Vue) consumindo a API
- [ ] 📊 Dashboard de métricas no Application Insights
- [ ] 🧪 Testes automatizados no workflow
- [ ] ⬆️ Migrar para Python 3.11 (deadline 3.10: out/2026)
- [ ] 🌍 Configurar CORS para domínios específicos
- [ ] 💾 Persistência de conversas (Cosmos DB)

---

## 📚 Documentação adicional

- 📖 [**Guia de Configuração completo**](./guia-de-configuracao.md) — provisionamento, deploy, troubleshooting
- 🔗 [Azure Functions Python](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- 🔗 [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- 🔗 [GPT-5 API Reference](https://platform.openai.com/docs/guides/reasoning)
- 🔗 [Flex Consumption Plan](https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan)

---

## 👤 Autor

**Erick Medeiros**

- 🐙 GitHub: [@ErickMedeiros](https://github.com/ErickMedeiros)

---

## 📄 Licença

Este projeto é privado e foi desenvolvido para fins de estudo e demonstração.

---

<div align="center">

⭐ **Se este projeto te ajudou, considere dar uma estrela!** ⭐

Feito com ☕ e ⚡ usando **Azure Functions** + **Azure OpenAI**

</div>
