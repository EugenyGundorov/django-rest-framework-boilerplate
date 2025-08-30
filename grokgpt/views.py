import uuid, json
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import GPTRequest
from .tasks import process_gpt_request  # <-- только синхронный импорт

# API-ключ для внешних вызовов
def require_api_key(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        key = request.headers.get('X-API-KEY') or request.GET.get('api_key')
        if not key or key != settings.CHATGPT_API_KEY:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped

@csrf_exempt
@require_api_key
def submit_request(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid method"}, status=405)

    data = json.loads(request.body)
    id_client     = data.get('id_client')
    system_prompt = data.get('system_prompt')
    user_message  = data.get('user_message')
    model         = data.get('model', 'gpt-3.5-turbo')
    api_key       = data.get('api_key')

    # Сохраняем «заглушку» в базе
    request_id = str(uuid.uuid4())
    GPTRequest.objects.create(
        request_id=request_id,
        client_id=id_client,
        system_prompt=system_prompt,
        user_message=user_message,
        model=model
    )

    # Уходим в фон через Celery
    process_gpt_request.apply_async(
        args=[id_client, request_id, system_prompt, user_message, model, api_key]
    )

    return JsonResponse({"request_id": request_id})

@csrf_exempt
@require_api_key
def check_status(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Invalid method"}, status=405)
    rid = request.GET.get('request_id')
    try:
        r = GPTRequest.objects.get(request_id=rid)
        return JsonResponse({"completed": r.completed})
    except GPTRequest.DoesNotExist:
        return JsonResponse({"error": "Request not found"}, status=404)

@csrf_exempt
@require_api_key
def get_result(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Invalid method"}, status=405)
    rid = request.GET.get('request_id')
    try:
        r = GPTRequest.objects.get(request_id=rid)
        if not r.completed:
            return JsonResponse({"error": "Request not completed yet"}, status=202)
        return JsonResponse({"response": r.response_text})
    except GPTRequest.DoesNotExist:
        return JsonResponse({"error": "Request not found"}, status=404)

@csrf_exempt
@require_api_key
def health_check(request):
    return JsonResponse({"status": "ok", "api": "chatgpt_async"})
