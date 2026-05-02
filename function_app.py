import logging
import json
import os
import azure.functions as func
from openai import AzureOpenAI, APIError, APIConnectionError, RateLimitError

app = func.FunctionApp()

# Cliente inicializado uma vez e reutilizado entre invocações na mesma instância
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

    # Parse do body
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "Body deve ser JSON válido"}, 400)

    user_message = (body or {}).get("message", "").strip()
    if not user_message:
        return _json_response({"error": "Campo 'message' é obrigatório"}, 400)

    # Validação de configuração
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
            model=deployment,  # No Azure, "model" recebe o NOME DA DEPLOYMENT
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente técnico especializado em Azure.",
                },
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=4000,        # Margem ampla para reasoning + resposta
            reasoning_effort="minimal",        # GPT-5: minimal | low | medium | high
            # Sem 'temperature' — GPT-5 só aceita o default (=1)
        )

        # Logs de diagnóstico (úteis pra debugar reasoning vs. resposta visível)
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