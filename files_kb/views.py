
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db import connection
from django.conf import settings

from .models import FileAsset, KnowledgeChunk
from .tasks import index_file_sync

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

class IndexSerializer(serializers.Serializer):
    filename = serializers.CharField()
    storage_url = serializers.URLField()
    size_bytes = serializers.IntegerField(required=False, default=0)
    content_type = serializers.CharField(required=False, allow_blank=True, default="")

class IndexView(APIView):
    @extend_schema(request=IndexSerializer, responses={200: dict})
    def post(self, request):
        ser = IndexSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = FileAsset.objects.create(**ser.validated_data)
        index_file_sync(obj.id)
        return Response({"ok": True, "file_id": obj.id})

class SearchSerializer(serializers.Serializer):
    query = serializers.CharField()
    top_k = serializers.IntegerField(required=False, default=5)
    api_key = serializers.CharField(required=False, allow_blank=True, default="")
    model = serializers.CharField(required=False, allow_blank=True, default="text-embedding-3-small")

def embed_text(text: str, api_key: str, model: str="text-embedding-3-small"):
    if not OpenAI:
        raise RuntimeError("openai package not available")
    key = api_key or settings.OPENAI_API_KEY
    if not key:
        raise RuntimeError("OPENAI_API_KEY not provided")
    client = OpenAI(api_key=key)
    out = client.embeddings.create(model=model, input=text)
    return out.data[0].embedding

class SearchView(APIView):
    @extend_schema(request=SearchSerializer, responses={200: dict})
    def post(self, request):
        ser = SearchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        q = ser.validated_data["query"]
        top_k = ser.validated_data["top_k"]
        api_key = ser.validated_data.get("api_key","")
        model = ser.validated_data.get("model","text-embedding-3-small")

        vec = embed_text(q, api_key, model)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, title, content FROM files_kb_knowledgechunk ORDER BY embedding <=> %s LIMIT %s",
                [vec, top_k]
            )
            rows = cur.fetchall()
        results = [{"id": r[0], "title": r[1], "content": r[2]} for r in rows]
        return Response({"ok": True, "results": results})
