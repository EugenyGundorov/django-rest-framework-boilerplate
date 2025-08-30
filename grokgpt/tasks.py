# grokgpt/tasks.py — REWRITTEN to call xAI Grok with extended params (key_api, files, history, model)

from celery import shared_task
import requests, logging, json
from .models import GPTRequest

logger = logging.getLogger(__name__)

def _split_by_limit(text: str, limit: int) -> list[str]:
    if not limit or limit <= 0:
        return [text]
    # Split by paragraphs and try to pack without breaking words
    import re as _re
    paras = _re.split(r'\n{2,}', text.strip())
    chunks, buf = [], ""
    sep = ""
    def flush():
        nonlocal buf
        if buf:
            chunks.append(buf)
            buf = ""
    for p in paras:
        if len(p) <= limit:
            if len(buf) + len(sep) + len(p) <= limit:
                buf = f"{buf}{sep}{p}"
            else:
                flush(); buf = p
            sep = "\n\n"
            continue
        # paragraph is too long — split by sentences
        sentences = _re.split(r'(?<=[\.\!\?])\s+', p)
        for s in sentences:
            if len(s) <= limit:
                if len(buf) + len(sep) + len(s) <= limit:
                    buf = f"{buf}{sep}{s}"
                else:
                    flush(); buf = s
                sep = " "
            else:
                # fallback hard split
                for i in range(0, len(s), limit):
                    piece = s[i:i+limit]
                    if len(buf) + len(sep) + len(piece) <= limit:
                        buf = f"{buf}{sep}{piece}"
                    else:
                        flush(); buf = piece
                sep = ""
        sep = "\n\n"
    flush()
    return chunks

def _to_telegram_html(text: str) -> str:
    # Minimal safe formatting for Telegram HTML
    import html, re as _re
    t = html.escape(text)
    # bold: **...**  -> <b>...</b>
    t = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    # italic: _..._ or *...* -> <i>...</i> (avoid conflict with bold)
    t = _re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    t = _re.sub(r"_(.+?)_", r"<i>\1</i>", t)
    # inline code: `...` -> <code>...</code>
    t = _re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def _normalize_messages(system_prompt, user_message, assyst_promt=None, history=None, files=None, knowledge=None):
    messages = []
    if (system_prompt or '').strip():
        messages.append({'role': 'system', 'content': system_prompt})
    if assyst_promt:
        messages.append({'role': 'system', 'content': f'[AGENT]\n{assyst_promt}'})
    if history:
        for m in history:
            if isinstance(m, dict) and 'role' in m and 'content' in m:
                messages.append({'role': m['role'], 'content': m['content']})
    if (user_message or '').strip():
        messages.append({'role': 'user', 'content': user_message})
    if files:
        for f in files:
            name = f.get('name') if isinstance(f, dict) else None
            content = f.get('content') if isinstance(f, dict) else None
            role = (f.get('role') or 'system') if isinstance(f, dict) else 'system'
            if content:
                messages.append({'role': role, 'content': f"[FILE] {name or 'attachment'}\n{content}"})
    if knowledge:
        for item in knowledge:
            title = item.get('title', 'Knowledge')
            content = item.get('content', '')
            if content:
                messages.append({'role': 'system', 'content': f"[KB] {title}\n{content}"})
    return messages

@shared_task
def process_gpt_request(
    key_api, id_client, request_id, system_prompt, user_message, model,
    agent_key=None, assyst_promt=None, model_settings=None,
    files=None, knowledge=None, history=None, sb_key=None,
    use_stream=True, max_chars=None, format_html=False
):
    """xAI Grok Chat Completions with extended parameters.
    Saves the response text into GPTRequest and marks it completed.
    """
    try:
        headers = {
            'Authorization': f'Bearer {key_api}',
            'Content-Type': 'application/json',
        }
        messages = _normalize_messages(system_prompt, user_message, assyst_promt, history, files, knowledge)
        payload = {
            'model': model or 'grok-4-latest',
            'messages': messages,
        }
        timeout = 60
        if isinstance(model_settings, dict):
            timeout = model_settings.get('timeout', timeout)
            for k, v in model_settings.items():
                if k not in payload and k != 'timeout':
                    payload[k] = v

        content = None
        if use_stream:
            # Streaming SSE
            payload['stream'] = True
            with requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=payload, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                parts = []
                for raw_line in r.iter_lines(decode_unicode=False):
                    if not raw_line:
                        continue
                    line = raw_line.decode('utf-8', errors='ignore')
                    if not line.startswith('data: '):
                        continue
                    data_line = line[6:].strip()
                    if data_line == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_line)
                    except Exception:
                        continue
                    delta = chunk.get('choices', [{}])[0].get('delta', {}).get('content')
                    if delta:
                        parts.append(delta)
            content = ''.join(parts).strip()
            if not content:
                content = ""
        else:
            # Non-streaming
            resp = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            try:
                content = data['choices'][0]['message']['content']
            except Exception:
                content = f"Invalid Grok response: {data!r}"

        final_text = _to_telegram_html(content) if format_html else content
        chunks = _split_by_limit(final_text, int(max_chars) if max_chars else 0)

        # сохраняем полный текст (без потери), не обрезая под лимит
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=final_text,
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
        logger.exception("xAI/Grok request timeout for request_id=%s", request_id)
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text="Ошибка: превышено время ожидания ответа от xAI/Grok.",
            completed=False
        )
        return False
    except requests.exceptions.HTTPError as e:
        logger.error("xAI/Grok returned %s: %s", getattr(e.response, 'status_code', None), getattr(e.response, 'text', ''))
        resp = getattr(e, 'response', None)
        text = getattr(resp, 'text', '') if resp is not None else ''
        status = getattr(resp, 'status_code', '')
        GPTRequest.objects.filter(request_id=request_id).update(
            response_text=f"xAI/Grok HTTPError {status}: {text}",
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
