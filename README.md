@"
# zafitec-ai-chat

Azure Functions Python app que expõe um endpoint HTTP de chat usando Azure OpenAI (GPT-5-nano).

## Endpoint

\`POST /api/chat\`

### Body

\`\`\`json
{
  "message": "Sua pergunta aqui"
}
\`\`\`

### Response

\`\`\`json
{
  "response": "Resposta do modelo"
}
\`\`\`

## Stack

- **Runtime:** Python 3.10
- **Plano:** Azure Functions Flex Consumption
- **Modelo:** Azure OpenAI – gpt-5-nano
- **Deploy:** GitHub Actions (\`.github/workflows/deploy.yml\`)

## Variáveis de ambiente esperadas

Configuradas como Application Settings no Azure Function App:

- \`AZURE_OPENAI_ENDPOINT\`
- \`AZURE_OPENAI_API_KEY\`
- \`AZURE_OPENAI_DEPLOYMENT\`
- \`AZURE_OPENAI_API_VERSION\`

## Desenvolvimento local

\`\`\`powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
func start
\`\`\`
"@ | Out-File -FilePath .\README.md -Encoding utf8 -Force