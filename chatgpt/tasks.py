# chatgpt/tasks.py

from celery import shared_task
import requests, logging
from django.conf import settings
from .models import GPTRequest

logger = logging.getLogger(__name__)

@shared_task
def process_gpt_request(id_client, request_id, system_prompt, user_message, model, api_key):
    headers = {
        'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_message},
        ]
    }

    try:
        # timeout = (connect_timeout, read_timeout)
        # чтобы GPT «думал» не более 4 секунд и соединение не висело дольше 8 секунд:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=(10, 60)   # 4s на соединение, 4s на чтение
        )
        resp.raise_for_status()

        reply = resp.json()["choices"][0]["message"]["content"]
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=reply,
            completed=True
        )

        # Webhook Salebot
        callback_url = f"https://chatter.salebot.pro/api/{api_key}/callback"
        cb_body = {"client_id": id_client, "message": f"gptcomplite_{request_id}"}
        requests.post(callback_url, json=cb_body)

    except requests.exceptions.ReadTimeout:
        # timed out
        logger.error("OpenAI request timed out for request_id=%s", request_id)
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text="Ошибка: превышено время ожидания ответа от OpenAI.",
            completed=False
        )
    except requests.exceptions.HTTPError as e:
        logger.error("OpenAI returned %s: %s", resp.status_code, resp.text)
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=f"OpenAI HTTPError {resp.status_code}: {resp.text}",
            completed=False
        )
    except Exception as e:
        logger.exception("Unexpected error for request_id=%s", request_id)
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=f"Неожиданная ошибка: {e}",
            completed=False
        )
