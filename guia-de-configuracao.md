# Guia de Configuração — Deploy de Azure Function App com Azure OpenAI

Este documento descreve, do início ao fim, o processo completo para implantar uma Azure Function App em **Flex Consumption** integrada ao **Azure OpenAI (GPT-5-nano)**, com pipeline de deploy automatizado via **GitHub Actions**.

A receita aqui foi validada em produção no projeto `zafitec-ai-chat`.

---

## Sumário

1. [Visão geral da arquitetura](#1-visão-geral-da-arquitetura)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Provisionamento dos recursos no Azure](#3-provisionamento-dos-recursos-no-azure)
4. [Estrutura do projeto](#4-estrutura-do-projeto)
5. [Código da Function](#5-código-da-function)
6. [Configuração local](#6-configuração-local)
7. [Application Settings no Azure](#7-application-settings-no-azure)
8. [Teste local](#8-teste-local)
9. [Service Principal para GitHub Actions](#9-service-principal-para-github-actions)
10. [Workflow do GitHub Actions](#10-workflow-do-github-actions)
11. [Push e primeiro deploy](#11-push-e-primeiro-deploy)
12. [Validação em produção](#12-validação-em-produção)
13. [Receita para próximos deploys](#13-receita-para-próximos-deploys)
14. [Troubleshooting](#14-troubleshooting)
15. [Particularidades do GPT-5](#15-particularidades-do-gpt-5)
16. [Particularidades do Flex Consumption](#16-particularidades-do-flex-consumption)

---

## 1. Visão geral da arquitetura

```
┌─────────────┐      git push      ┌─────────────────┐
│   Cliente   │ ────────────────▶  │  GitHub Repo    │
│  (Postman/  │                    │  (main / deploy)│
│   browser)  │                    └────────┬────────┘
└──────┬──────┘                             │
       │ HTTP POST                          │ workflow_run
       │ /api/chat                          ▼
       │                            ┌──────────────────┐
       │                            │ GitHub Actions   │
       │                            │ - setup Python   │
       │                            │ - pip install    │
       │                            │ - azure/login    │
       │                            │ - functions-     │
       │                            │   action@v1      │
       │                            └────────┬─────────┘
       │                                     │ deploy
       ▼                                     ▼
┌──────────────────────────────────────────────────────┐
│         Azure Function App (Flex Consumption)        │
│              zafitec-ai-chat                         │
│                                                      │
│  function_app.py  →  HttpChat (POST /api/chat)       │
└──────────────────────┬───────────────────────────────┘
                       │ chat.completions.create
                       ▼
              ┌──────────────────────┐
              │  Azure OpenAI        │
              │  gpt-5-nano          │
              │  (East US 2)         │
              └──────────────────────┘
```

**Componentes:**

- **Azure Function App** em plano **Flex Consumption** (Linux, Python 3.10)
- **Azure OpenAI** com deployment do modelo `gpt-5-nano`
- **GitHub Actions** para CI/CD automatizado
- **Service Principal** com role `Contributor` restrita ao Function App

---

## 2. Pré-requisitos

Instale e configure os seguintes itens antes de começar:

- **Conta Azure** com permissão para criar recursos
- **Azure CLI** versão 2.55+ (`az --version`)
- **Azure Functions Core Tools** v4.0.5530+ (`func --version`)
- **Python 3.10** (`py -3.10 --version` no Windows)
- **Git** (`git --version`)
- **Conta GitHub** com permissão para criar repositórios e secrets
- Editor de código (VS Code recomendado)
- Cliente HTTP para testes (Postman, Insomnia, ou `Invoke-RestMethod` no PowerShell)

> ⚠️ A Azure CLI clássica **não suporta todos os comandos do Flex Consumption**. Mantenha-a sempre atualizada com `az upgrade`.

---

## 3. Provisionamento dos recursos no Azure

### 3.1 — Criar Resource Group

```powershell
az group create --name RG-AISERVICES --location canadacentral
```

### 3.2 — Criar Azure OpenAI

Recomenda-se criar pelo portal para selecionar a região com disponibilidade do modelo desejado:

1. Portal → **Create a resource** → **Azure OpenAI**
2. Resource Group: `RG-AISERVICES`
3. Region: uma com disponibilidade de **GPT-5** (ex.: `East US 2`)
4. Name: livre (ex.: `erick-mooe7h51-eastus2`)
5. Pricing tier: Standard S0
6. Após criação, vá em **Azure OpenAI Studio** → **Deployments** → **Create new deployment**
7. Model: `gpt-5-nano` (ou outra variante GPT-5)
8. Deployment name: `gpt-5-nano` (ou nome de sua escolha — esse é o valor que vai em `AZURE_OPENAI_DEPLOYMENT`)

### 3.3 — Criar Function App em Flex Consumption

```powershell
# Cria storage account associado
az storage account create `
  --name zafitecstorage `
  --resource-group RG-AISERVICES `
  --location canadacentral `
  --sku Standard_LRS

# Cria Function App em Flex Consumption (Python 3.10, Linux)
az functionapp create `
  --resource-group RG-AISERVICES `
  --name zafitec-ai-chat `
  --storage-account zafitecstorage `
  --flexconsumption-location canadacentral `
  --runtime python `
  --runtime-version 3.10 `
  --functions-version 4
```

> 💡 A flag chave aqui é `--flexconsumption-location`. Sem ela, o app é criado em **Consumption clássico** (que tem outro fluxo de deploy).

### 3.4 — Confirmar configuração

```powershell
az functionapp show -n zafitec-ai-chat -g RG-AISERVICES --query "properties.sku" -o tsv
# Esperado: FlexConsumption

az functionapp show -n zafitec-ai-chat -g RG-AISERVICES --query "properties.functionAppConfig.runtime" -o json
# Esperado: { "name": "python", "version": "3.10" }
```

> ⚠️ Em Flex Consumption, **a versão do runtime fica em `properties.functionAppConfig.runtime`**, não em `properties.siteConfig.linuxFxVersion` (que é o lugar do Consumption clássico).

---

## 4. Estrutura do projeto

```
zafitec-ai-chat/
├── .github/
│   └── workflows/
│       └── deploy.yml              # Pipeline GitHub Actions
├── .funcignore                     # Exclusões do empacotamento
├── .gitignore                      # Exclusões do Git
├── function_app.py                 # Código da Function
├── host.json                       # Config do host
├── local.settings.json             # Config local (NÃO commitar)
├── README.md
├── guia-de-configuracao.md         # Este documento
└── requirements.txt                # Dependências Python
```

---

## 5. Código da Function

### 5.1 — `function_app.py`

```python
import logging
import json
import os
import azure.functions as func
from openai import AzureOpenAI, APIError, APIConnectionError, RateLimitError

app = func.FunctionApp()

_client = None


def get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        _client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
    return _client


@app.function_name(name="HttpChat")
@app.route(
    route="chat",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def http_chat(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("HttpChat function iniciada")

    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "Body deve ser JSON válido"}, 400)

    user_message = (body or {}).get("message", "").strip()
    if not user_message:
        return _json_response({"error": "Campo 'message' é obrigatório"}, 400)

    required = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logging.error("Variáveis de ambiente ausentes: %s", missing)
        return _json_response({"error": "Configuração do servidor incompleta"}, 500)

    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    try:
        client = get_client()
        completion = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente técnico especializado em Azure.",
                },
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=4000,
            reasoning_effort="minimal",
        )

        logging.info("Finish reason: %s", completion.choices[0].finish_reason)
        logging.info("Usage: %s", completion.usage)

        answer = completion.choices[0].message.content or "(resposta vazia do modelo)"
        return _json_response({"response": answer}, 200)

    except RateLimitError:
        logging.warning("Rate limit atingido no Azure OpenAI")
        return _json_response(
            {"error": "Serviço sobrecarregado, tente novamente em instantes"}, 429
        )
    except APIConnectionError as e:
        logging.error("Falha de conexão com Azure OpenAI: %s", e)
        return _json_response({"error": "Falha ao contatar o serviço de IA"}, 502)
    except APIError as e:
        logging.error("Erro da API Azure OpenAI: %s", e)
        return _json_response({"error": "Erro ao processar a requisição"}, 502)
    except Exception:
        logging.exception("Erro inesperado")
        return _json_response({"error": "Erro interno"}, 500)


def _json_response(payload: dict, status: int) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        mimetype="application/json",
        status_code=status,
    )
```

**Pontos-chave do código:**

- **Cliente reutilizado** entre invocações (`_client` global) — reduz latência em cold-restart parcial.
- **`max_completion_tokens=4000`** (não `max_tokens`) — GPT-5 usa esse parâmetro.
- **`reasoning_effort="minimal"`** — minimiza tokens gastos em raciocínio interno do GPT-5, deixando margem para a resposta visível.
- **Sem `temperature`** — GPT-5 só aceita o default (=1).
- **Tratamento granular de erros** — distingue rate limit, falha de conexão, erro de API e erro genérico.
- **Logs com `finish_reason` e `usage`** — facilita diagnóstico em Application Insights.

### 5.2 — `host.json`

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  },
  "functionTimeout": "00:05:00"
}
```

### 5.3 — `requirements.txt`

```
azure-functions==1.21.3
openai==1.59.6
```

> ⚠️ **Versões fixadas (pinned)** são essenciais. Sem elas, builds futuros podem quebrar quando o `openai` mudar de major version. A versão `1.59.6` é compatível com `httpx 0.28+`, evitando o bug `Client.__init__() got an unexpected keyword argument 'proxies'`.

### 5.4 — `.funcignore`

```
.git*
.vscode
__pycache__
.venv
.python_packages
local.settings.json
tests
*.pyc
.pytest_cache
.env
*.md
```

### 5.5 — `.gitignore`

```
# Python
.venv/
.python_packages/
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# Azure Functions
local.settings.json
bin/
obj/
_staging/
deploy.zip
cred.json

# IDE
.vscode/
.idea/
*.swp

# Sistema
.DS_Store
Thumbs.db

# Logs
*.log
```

> 🔒 **`local.settings.json` deve estar SEMPRE no `.gitignore`**. Esse arquivo contém a chave do Azure OpenAI e nunca deve ir para o repositório.

---

## 6. Configuração local

### 6.1 — `local.settings.json`

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

> 💡 O endpoint do Azure OpenAI no formato novo (AI Foundry / multi-service) usa o domínio `cognitiveservices.azure.com`. O formato legado `openai.azure.com` ainda funciona para recursos provisionados antes da migração.

### 6.2 — Criar venv local

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> ⚠️ Sempre confira que o prompt mostra `(.venv)` antes de instalar dependências. Sem o venv ativo, o pip instala no Python global, o que polui o ambiente e gera inconsistências.

---

## 7. Application Settings no Azure

```powershell
az functionapp config appsettings set `
  -n zafitec-ai-chat `
  -g RG-AISERVICES `
  --settings `
    AZURE_OPENAI_ENDPOINT="https://<seu-recurso>.cognitiveservices.azure.com/" `
    AZURE_OPENAI_API_KEY="<sua-chave>" `
    AZURE_OPENAI_DEPLOYMENT="gpt-5-nano" `
    AZURE_OPENAI_API_VERSION="2025-01-01-preview"
```

> ⚠️ **Em Flex Consumption, as seguintes app settings são INVÁLIDAS** (causam erro ao serem aplicadas):
> - `FUNCTIONS_WORKER_RUNTIME` (gerenciado via `functionAppConfig.runtime`)
> - `SCM_DO_BUILD_DURING_DEPLOYMENT` (não há SCM no Flex)
> - `ENABLE_ORYX_BUILD` (build é gerenciado pela plataforma)
> - `WEBSITE_RUN_FROM_PACKAGE`
>
> Tente removê-las se existirem:
> ```powershell
> az functionapp config appsettings delete -n zafitec-ai-chat -g RG-AISERVICES `
>   --setting-names SCM_DO_BUILD_DURING_DEPLOYMENT ENABLE_ORYX_BUILD WEBSITE_RUN_FROM_PACKAGE
> ```

---

## 8. Teste local

Antes de fazer qualquer deploy, valide localmente:

```powershell
func start
```

Em outro terminal:

```powershell
$body = @{ message = "Olá, está funcionando?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:7071/api/chat" -Method POST -ContentType "application/json" -Body $body
```

✅ Esperado: resposta JSON com o conteúdo do modelo. Se não funcionar localmente, **não publique** — corrija primeiro.

---

## 9. Service Principal para GitHub Actions

### 9.1 — Criar SP com permissão restrita ao Function App

```powershell
$subId = az account show --query id -o tsv

az ad sp create-for-rbac `
  --name "github-actions-zafitec-ai-chat" `
  --role Contributor `
  --scopes "/subscriptions/$subId/resourceGroups/RG-AISERVICES/providers/Microsoft.Web/sites/zafitec-ai-chat" `
  --json-auth
```

O comando retorna um JSON como:

```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "...",
  ...
}
```

> 🔒 **Esse JSON contém um secret. Trate-o como senha**:
> - Nunca commite no repositório
> - Cole **diretamente como secret no GitHub** (próximo passo)
> - Se perder, recrie o SP — não há recuperação

### 9.2 — Cadastrar como secret no GitHub

1. Acesse `https://github.com/<seu-usuario>/<seu-repo>/settings/secrets/actions`
2. **New repository secret**
3. **Name:** `AZURE_CREDENTIALS`
4. **Value:** o JSON completo do passo anterior
5. **Add secret**

---

## 10. Workflow do GitHub Actions

Crie o arquivo `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure Function App (Flex Consumption)

on:
  push:
    branches:
      - main
      - deploy/github-actions
  workflow_dispatch:

env:
  AZURE_FUNCTIONAPP_NAME: zafitec-ai-chat
  PYTHON_VERSION: '3.10'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout do repositório
        uses: actions/checkout@v4

      - name: Setup Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Resolve dependências e instala num target específico
        shell: bash
        run: |
          python -m pip install --upgrade pip
          pip install --target=".python_packages/lib/site-packages" -r requirements.txt

      - name: Login no Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy para o Azure Function App (Flex)
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ env.AZURE_FUNCTIONAPP_NAME }}
          package: '.'
          scm-do-build-during-deployment: false
          enable-oryx-build: false
          sku: 'flexconsumption'
```

**Pontos-chave do workflow:**

- **`pip install --target=".python_packages/lib/site-packages"`** — instala dependências numa pasta que o Functions Python reconhece como source de pacotes.
- **`sku: 'flexconsumption'`** — ativa o caminho específico do Flex na `functions-action`. **Essencial.**
- **`scm-do-build-during-deployment: false` + `enable-oryx-build: false`** — desativa flags de Consumption clássico que não fazem sentido no Flex.
- **`workflow_dispatch`** — permite disparar manualmente pelo botão "Run workflow".

> ⚠️ **Não crie esse arquivo via PowerShell here-string** (`@"..."@ | Out-File`). Caracteres como backtick e `${{` causam problemas de escape. Crie pelo VS Code ou outro editor de texto, salvando em UTF-8.

---

## 11. Push e primeiro deploy

### 11.1 — Inicializar git e criar branch

```powershell
git init
git config user.email "seu-email@exemplo.com"
git config user.name "Seu Nome"
git branch -M main
git checkout -b deploy/github-actions
```

### 11.2 — Adicionar arquivos e validar `.gitignore`

```powershell
git add .
git status
```

> ⚠️ **Confirme que `local.settings.json` NÃO aparece** na lista de arquivos a serem commitados. Se aparecer, revise o `.gitignore` antes de prosseguir.

### 11.3 — Commit e push

```powershell
git commit -m "feat: setup inicial do Function App com deploy via GitHub Actions"

git remote add origin https://github.com/<seu-usuario>/<seu-repo>.git
git push -u origin deploy/github-actions
```

O push **dispara automaticamente** o workflow (configurado em `on.push.branches`).

### 11.4 — Acompanhar o deploy

Acesse `https://github.com/<seu-usuario>/<seu-repo>/actions` e clique no workflow em execução.

✅ Esperado: todos os steps verdes em 2-7 minutos:
- Checkout do repositório
- Setup Python 3.10
- Resolve dependências
- Login no Azure
- Deploy para o Azure Function App (Flex)

---

## 12. Validação em produção

### 12.1 — Verificar registro da função

```powershell
az functionapp function list -n zafitec-ai-chat -g RG-AISERVICES --query "[].name" -o tsv
```

✅ Esperado: `HttpChat`

### 12.2 — Testar o endpoint

```powershell
$body = @{ message = "Olá em produção?" } | ConvertTo-Json
Invoke-RestMethod -Uri "https://zafitec-ai-chat.azurewebsites.net/api/chat" `
  -Method POST -ContentType "application/json" -Body $body
```

✅ Esperado: JSON com `response` contendo a resposta do modelo.

> ⏱️ A **primeira chamada após deploy pode demorar 30-60s** (cold start do worker Python). Chamadas subsequentes ficam abaixo de 5s.

### 12.3 — Monitorar logs

No portal Azure → **Function App `zafitec-ai-chat`** → **Monitoring → Log stream**.

> ⚠️ `az webapp log tail` **não funciona em Flex Consumption** porque o endpoint SCM (Kudu) não existe nesse plano. Use o portal ou Application Insights.

---

## 13. Receita para próximos deploys

A partir daqui, o ciclo completo é:

```powershell
# 1. Edite o código localmente
# 2. (Opcional) Teste local
func start

# 3. Commit e push
git add .
git commit -m "descrição da mudança"
git push
```

O GitHub Actions detecta o push, faz build, deploya no Flex, e em ~2 min está em produção.

Para mergear o trabalho da branch de deploy para `main`:

```powershell
git checkout main
git merge deploy/github-actions
git push origin main
```

---

## 14. Troubleshooting

### 14.1 — Erro 404 no `func azure functionapp publish`

**Causa:** o `func` ainda não suporta totalmente Flex Consumption — ele tenta o endpoint SCM (Kudu), que não existe nesse plano.

**Solução:** use GitHub Actions (este guia) ou o comando `az functionapp deploy` específico para Flex.

### 14.2 — `'3.10' não é reconhecido como um comando interno`

**Causa:** PowerShell interpretando o `|` em `Python|3.10` como pipe de comando.

**Solução:** use `az --%`:
```powershell
az --% functionapp config set -n <app> -g <rg> --linux-fx-version "Python|3.10"
```

### 14.3 — `Client.__init__() got an unexpected keyword argument 'proxies'`

**Causa:** incompatibilidade entre `openai<1.55` e `httpx>=0.28`.

**Solução:** atualize `openai` para `1.59.6` ou superior no `requirements.txt`.

### 14.4 — Função deploya mas não aparece em `az functionapp function list`

**Causa em Flex:** o ZIP enviado pelo `az functionapp deployment source config-zip` tinha estrutura inadequada, ou faltavam dependências, ou o sync de triggers ainda não terminou.

**Solução:**
1. Use GitHub Actions (resolve estrutura automaticamente).
2. Aguarde 60s adicionais após "Deployment was successful".
3. Verifique no portal → **Functions** se a função aparece.

### 14.5 — Resposta `200 OK` mas `"response": ""`

**Causa:** `max_completion_tokens` baixo demais — todos os tokens foram consumidos pelo raciocínio interno do GPT-5, sobrando zero para a resposta visível.

**Solução:** aumentar `max_completion_tokens` para 4000+ e definir `reasoning_effort="minimal"` para chats simples.

### 14.6 — Erro 415 (Unsupported Media Type) em deploy via REST

**Causa:** chamando endpoint clássico (`onedeploy`) em vez do endpoint específico do Flex.

**Solução:** use GitHub Actions com `Azure/functions-action@v1` e `sku: 'flexconsumption'`.

### 14.7 — `Invalid command. This is not currently supported for Azure Functions on the Flex Consumption plan.`

**Causa:** comando que tentou foi descontinuado ou nunca existiu para Flex (ex.: `az functionapp deployment list-publishing-credentials`).

**Solução:** use o método de deploy via GitHub Actions descrito neste guia.

---

## 15. Particularidades do GPT-5

GPT-5 (incluindo `gpt-5-nano`, `gpt-5-mini`, `gpt-5`) é uma família de **modelos de raciocínio**. Tem regras estritas:

| Parâmetro | GPT-4o e anteriores | GPT-5 |
|---|---|---|
| `max_tokens` | ✅ | ❌ Erro 400 |
| `max_completion_tokens` | ✅ | ✅ **Use este** |
| `temperature` | qualquer valor | só default (=1) |
| `top_p` | qualquer valor | só default |
| `reasoning_effort` | n/a | `minimal` \| `low` \| `medium` \| `high` |

**`reasoning_effort` na prática:**

- **`minimal`** — quase sem raciocínio, resposta direta. Ideal para chat geral, FAQ, traduções.
- **`low`** — raciocínio leve. Bom para tarefas que precisam de algum contexto.
- **`medium`** — padrão. Equilíbrio.
- **`high`** — usa muito reasoning. Para problemas complexos (matemática, código, análise profunda).

**Sintoma de resposta vazia:** quando todos os tokens são consumidos pelo raciocínio. Diagnóstico via `completion.usage.completion_tokens_details.reasoning_tokens` no log.

---

## 16. Particularidades do Flex Consumption

Flex Consumption (lançado em 2024) é um plano novo do Azure Functions com diferenças significativas em relação ao Consumption clássico:

| Aspecto | Consumption clássico | Flex Consumption |
|---|---|---|
| Endpoint SCM (`*.scm.azurewebsites.net`) | ✅ existe | ❌ não existe |
| `linuxFxVersion` (config) | usado | ignorado |
| `functionAppConfig.runtime` | n/a | **fonte da verdade** |
| `FUNCTIONS_WORKER_RUNTIME` (app setting) | obrigatório | **inválido** |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | usado | inválido |
| `ENABLE_ORYX_BUILD` | usado | inválido |
| `func azure functionapp publish` | ✅ | ⚠️ parcialmente suportado |
| `az functionapp deployment list-publishing-credentials` | ✅ | ❌ |
| `az webapp log tail` | ✅ | ❌ |
| Logs em tempo real | Kudu LogStream | **Application Insights / portal Log stream** |
| Cold start | ~5-15s | ~30-60s primeira chamada após deploy |
| Deploy recomendado | `func publish` | **GitHub Actions com `sku: flexconsumption`** |

**Conclusão prática:** se está em Flex, esqueça boa parte da documentação genérica de Azure Functions e siga o caminho específico (GitHub Actions ou portal Deployment Center).

---

## Apêndice A — Stack final validada

| Item | Versão / Valor |
|---|---|
| Azure Functions Runtime | v4 |
| Plano | Flex Consumption |
| OS | Linux |
| Python | 3.10 |
| `azure-functions` | 1.21.3 |
| `openai` | 1.59.6 |
| Modelo Azure OpenAI | gpt-5-nano |
| API version | 2025-01-01-preview |
| Region (Function App) | Canada Central |
| Region (Azure OpenAI) | East US 2 |

## Apêndice B — Comandos úteis de manutenção

```powershell
# Listar funções registradas
az functionapp function list -n zafitec-ai-chat -g RG-AISERVICES --query "[].name" -o tsv

# Reiniciar Function App
az functionapp restart -n zafitec-ai-chat -g RG-AISERVICES

# Ver app settings (sem expor valores)
az functionapp config appsettings list -n zafitec-ai-chat -g RG-AISERVICES --query "[].name" -o tsv

# Ver runtime configurado (Flex)
az functionapp show -n zafitec-ai-chat -g RG-AISERVICES --query "properties.functionAppConfig.runtime"

# Confirmar SKU
az functionapp show -n zafitec-ai-chat -g RG-AISERVICES --query "properties.sku" -o tsv

# Disparar workflow manualmente via GitHub CLI
gh workflow run deploy.yml --ref deploy/github-actions
```

---

**Última atualização:** Maio/2026
**Versão do guia:** 1.0
**Validado em:** projeto `zafitec-ai-chat` em produção
