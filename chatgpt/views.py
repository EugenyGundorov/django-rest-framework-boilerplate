
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from .models import GPTRequest
from .ai_gateway import OpenAIClient, ModelParams, PromptParams, ClientData

import uuid
from .validators import validate_files
import asyncio

class SubmitSerializer(serializers.Serializer):
    request_id = serializers.CharField(required=False)
    client_id = serializers.CharField()
    gpt_api = serializers.CharField(required=False, default="openai")
    gpt_key = serializers.CharField(required=False, allow_blank=True, default="")
    agent_key = serializers.CharField(required=False, allow_blank=True, default="")
    base_url = serializers.CharField(required=False, allow_blank=True, default="")
    model = serializers.CharField(required=False, default="gpt-4o-mini")
    message_size = serializers.IntegerField(required=False, default=2048)
    system_prompt = serializers.CharField(required=False, allow_blank=True, default="")
    assist_promt = serializers.CharField(required=False, allow_blank=True, default="")
    assyst_promt = serializers.CharField(required=False, allow_blank=True, default="")
    user_message = serializers.CharField(required=False, allow_blank=True, default="")
    use_agent = serializers.BooleanField(required=False, default=False)
    files = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    knowledge = serializers.ListField(child=serializers.DictField(), required=False, default=list)

class SubmitView(APIView):
    @extend_schema(
        request=SubmitSerializer,
        responses={200: dict},
        examples=[OpenApiExample("Basic", value={"client_id":"abc","user_message":"Hi"})]
    )
    def post(self, request):
        ser = SubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        rid = data.get("request_id") or str(uuid.uuid4())
        # Validate files before saving
        asyncio.run(validate_files(data.get('files', [])))
        obj, created = GPTRequest.objects.update_or_create(
            request_id=rid,
            defaults = {
                "gpt_api": data["gpt_api"],
                "client_id": data["client_id"],
                "system_prompt": data["system_prompt"],
                "assist_promt": data["assist_promt"],
                "assyst_promt": data["assyst_promt"],
                "user_message": data.get("user_message",""),
                "model": data["model"],
                "gpt_key": data.get("gpt_key",""),
                "agent_key": data.get("agent_key",""),
                "message_size": data.get("message_size", 2048),
                "use_agent": data.get("use_agent", False),
                "files": data.get("files", []),
                "knowledge": data.get("knowledge", []),
                "completed": False,
                "response_text": "",
            }
        )
        # Process synchronously for simplicity here
        try:
            mp = ModelParams(model=obj.model, max_output=obj.message_size, base_url=request.data.get("base_url",""), api_key=(obj.gpt_key or ""))
            client = OpenAIClient(mp)
            if obj.use_agent:
                res = asyncio.run(client.run_agent(obj.assyst_promt or obj.assist_promt, obj.user_message, files=obj.files, knowledge=obj.knowledge))
            else:
                res = asyncio.run(client.generate(PromptParams(system=obj.system_prompt), ClientData(text=obj.user_message, images=obj.files)))
            obj.response_text = res.get("text","")
            obj.completed = True
            obj.save(update_fields=["response_text","completed"])
        except Exception as e:
            obj.response_text = f"ERROR: {e}"
            obj.completed = True
            obj.save(update_fields=["response_text","completed"])
        return Response({"ok": True, "request_id": obj.request_id})

class StatusView(APIView):
    @extend_schema(parameters=[OpenApiParameter("request_id", str, required=True)])
    def get(self, request):
        rid = request.GET.get("request_id","")
        try:
            obj = GPTRequest.objects.get(request_id=rid)
            return Response({"completed": obj.completed})
        except GPTRequest.DoesNotExist:
            return Response({"completed": False, "detail": "not found"}, status=404)

class ResultView(APIView):
    @extend_schema(parameters=[
        OpenApiParameter("request_id", str, required=True),
        OpenApiParameter("purge", bool, required=False, description="Очистить запись после выдачи результата")
    ])
    def get(self, request):
        rid = request.GET.get("request_id","")
        purge = request.GET.get("purge","false").lower() in ("1","true","yes")
        try:
            obj = GPTRequest.objects.get(request_id=rid)
            data = {"request_id": obj.request_id, "completed": obj.completed, "response_text": obj.response_text}
            if purge:
                obj.delete()
            return Response(data)
        except GPTRequest.DoesNotExist:
            return Response({"detail": "not found"}, status=404)

class CleanupView(APIView):
    @extend_schema(parameters=[OpenApiParameter("before", str, description="YYYY-MM-DD")])
    def post(self, request):
        before = request.data.get("before") or request.GET.get("before")
        if not before:
            return Response({"detail":"param 'before' required (YYYY-MM-DD)"}, status=400)
        try:
            dt = timezone.datetime.fromisoformat(before)
        except Exception:
            return Response({"detail":"invalid date format"}, status=400)
        qs = GPTRequest.objects.filter(created_at__lt=dt)
        n = qs.count()
        qs.delete()
        return Response({"deleted": n})

class HealthView(APIView):
    def get(self, request):
        return Response({"ok": True})
