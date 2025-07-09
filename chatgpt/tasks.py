from celery import shared_task
import requests, json
from django.conf import settings
from .models import GPTRequest

@shared_task
def process_gpt_request(id_client, request_id, system_prompt, user_message, model, api_key):
    # 1) Запрос к OpenAI
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        json=payload, headers=headers, timeout=10
    )
    resp.raise_for_status()
    reply = resp.json()["choices"][0]["message"]["content"]

    # 2) Сохраняем ответ
    GPTRequest.objects.filter(request_id=request_id).update(
        response_text=reply,
        completed=True
    )

    # 3) Webhook Salebot
    callback_url = f"https://chatter.salebot.pro/api/{api_key}/callback"
    cb_body = {"client_id": id_client, "message": f"gptcomplite_{request_id}"}
    requests.post(callback_url, json=cb_body)
