import uuid
import json
import aiohttp
import asyncio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import GPTRequest
from asgiref.sync import sync_to_async
from django.conf import settings

@csrf_exempt
def submit_request(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        id_client = data.get('id_client')
        system_prompt = data.get('system_prompt')
        user_message = data.get('user_message')
        model = data.get('model', 'gpt-3.5-turbo')
        api_key = data.get('api_key')

        request_id = str(uuid.uuid4())
        # Сохраняем запрос
        GPTRequest.objects.create(
            request_id=request_id,
            client_id=id_client,
            system_prompt=system_prompt,
            user_message=user_message,
            model=model
        )
        # Запускаем асинхронный процесс
        asyncio.create_task(process_gpt_request(id_client, request_id, system_prompt, user_message, model, api_key))
        return JsonResponse({"request_id": request_id})
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def check_status(request):
    if request.method == 'GET':
        request_id = request.GET.get('request_id')
        try:
            gpt_request = GPTRequest.objects.get(request_id=request_id)
            return JsonResponse({"completed": gpt_request.completed})
        except GPTRequest.DoesNotExist:
            return JsonResponse({"error": "Request not found"}, status=404)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def get_result(request):
    if request.method == 'GET':
        request_id = request.GET.get('request_id')
        try:
            gpt_request = GPTRequest.objects.get(request_id=request_id)
            if gpt_request.completed:
                return JsonResponse({"response": gpt_request.response_text})
            else:
                return JsonResponse({"error": "Request not completed yet"}, status=202)
        except GPTRequest.DoesNotExist:
            return JsonResponse({"error": "Request not found"}, status=404)
    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def health_check(request):
    """
    Тестовый метод для проверки работоспособности сервиса.
    Возвращает простую метку "status": "ok" и версию API.
    """
    return JsonResponse({"status": "ok", "api": "chatgpt_async"})

async def process_gpt_request(id_client, request_id, system_prompt, user_message, model, api_key):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.OPENAI_API_KEY}'
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as resp:
                response = await resp.json()
                reply = response["choices"][0]["message"]["content"]
                # Обновим запись в базе
                await sync_to_async(
                    GPTRequest.objects.filter(request_id=request_id).update
                )(
                    response_text=reply,
                    completed=True
                )
                # Отправка webhook в Salebot
                callback_url = f"https://chatter.salebot.pro/api/{api_key}/callback"
                callback_payload = {
                    "client_id": id_client,
                    "message": f"gptcomplite_{request_id}"
                }
                await session.post(
                    callback_url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(callback_payload)
                )
    except Exception as e:
        await sync_to_async(
            GPTRequest.objects.filter(request_id=request_id).update
        )(
            response_text=str(e),
            completed=False
        )