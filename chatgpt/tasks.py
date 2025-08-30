# chatgpt/tasks.py — REWRITTEN for extended params (key_api, agent_key, assyst_promt, model_settings, files, knowledge, history)

from celery import shared_task
import requests, logging
from django.conf import settings
from .models import GPTRequest

logger = logging.getLogger(__name__)

def _normalize_messages(system_prompt, user_message, assyst_promt=None, history=None, files=None, knowledge=None):
    messages = []
    if (system_prompt or '').strip():
        messages.append({'role': 'system', 'content': system_prompt})
    if assyst_promt:
        messages.append({'role': 'system', 'content': f'[AGENT]\n{assyst_promt}'})
    # prior chat
    if history:
        for m in history:
            if isinstance(m, dict) and 'role' in m and 'content' in m:
                messages.append({'role': m['role'], 'content': m['content']})
    # new user prompt
    if (user_message or '').strip():
        messages.append({'role': 'user', 'content': user_message})
    # inline files
    if files:
        for f in files:
            name = f.get('name') if isinstance(f, dict) else None
            content = f.get('content') if isinstance(f, dict) else None
            role = (f.get('role') or 'system') if isinstance(f, dict) else 'system'
            if content:
                messages.append({'role': role, 'content': f"[FILE] {name or 'attachment'}\n{content}"})
    # inline knowledge base
    if knowledge:
        for item in knowledge:
            title = item.get('title', 'Knowledge')
            content = item.get('content', '')
            if content:
                messages.append({'role': 'system', 'content': f"[KB] {title}\n{content}"})
    return messages

@shared_task
def process_gpt_request(id_client, request_id, system_prompt, user_message, model, key_api,
                        agent_key=None, assyst_promt=None, model_settings=None,
                        files=None, knowledge=None, history=None, sb_key=None):
    """OpenAI Chat Completions with extended parameters.
    Saves the response text into GPTRequest and marks it completed.
    """
    try:
        # select key
        api_key = key_api or settings.OPENAI_API_KEY
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        # build payload
        messages = _normalize_messages(system_prompt, user_message, assyst_promt, history, files, knowledge)
        payload = {
            'model': model or 'gpt-4o-mini',
            'messages': messages,
        }
        timeout = 60
        if isinstance(model_settings, dict):
            timeout = model_settings.get('timeout', timeout)
            # copy custom settings (e.g., temperature, max_tokens, top_p, response_format, tools, etc.)
            for k, v in model_settings.items():
                if k not in payload and k != 'timeout':
                    payload[k] = v

        resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        try:
            content = data['choices'][0]['message']['content']
        except Exception:
            content = f"Invalid OpenAI response: {data!r}"

        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=content,
            completed=True
        )
        # Webhook Salebot
        if sb_key:
            try:
                callback_url = f"https://chatter.salebot.pro/api/{sb_key}/callback"
                cb_body = {"client_id": id_client, "message": f"gptcomplite_{request_id}"}
                requests.post(callback_url, json=cb_body, timeout=10)
            except Exception:
                logger.exception("Salebot callback failed for request_id=%s", request_id)
        return True
    except requests.exceptions.Timeout:
        logger.exception("OpenAI request timeout for request_id=%s", request_id)
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text="Ошибка: превышено время ожидания ответа от OpenAI.",
            completed=False
        )
        return False
    except requests.exceptions.HTTPError as e:
        resp = getattr(e, 'response', None)
        status = getattr(resp, 'status_code', None)
        text = getattr(resp, 'text', '')
        logger.error("OpenAI returned %s: %s", status, text)
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=f"OpenAI HTTPError {status}: {text}",
            completed=False
        )
        return False
    except Exception as e:
        logger.exception("Unexpected error for request_id=%s", request_id)
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=f"Неожиданная ошибка: {e}",
            completed=False
        )
        return False