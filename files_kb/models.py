
from django.db import models
from django.conf import settings
from django_pgvector.fields import VectorField

class FileAsset(models.Model):
    id = models.BigAutoField(primary_key=True)
    filename = models.CharField(max_length=255)
    storage_url = models.URLField(max_length=1024, blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True, default="")
    checksum = models.CharField(max_length=64, blank=True, default="")
    source = models.CharField(max_length=50, blank=True, default="upload")  # upload|url|generated
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

class KnowledgeChunk(models.Model):
    id = models.BigAutoField(primary_key=True)
    file = models.ForeignKey(FileAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="chunks")
    title = models.CharField(max_length=255, blank=True, default="")
    content = models.TextField()
    # Vector embedding for pgvector; if not installed, you may skip creating extension
    embedding = VectorField(dimensions=1536, null=True, blank=True)  # size depends on model
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
        ]

class IndexJob(models.Model):
    id = models.BigAutoField(primary_key=True)
    file = models.ForeignKey(FileAsset, on_delete=models.CASCADE, related_name="index_jobs")
    status = models.CharField(max_length=20, default="queued")  # queued|running|done|failed
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
