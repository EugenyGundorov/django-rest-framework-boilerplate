
import hashlib
from django.conf import settings
from django.db import transaction
from files_kb.models import FileAsset, KnowledgeChunk, IndexJob

def index_file_sync(file_id: int, text_split: int = 1200):
    job = IndexJob.objects.create(file_id=file_id, status="running")
    try:
        file = FileAsset.objects.get(id=file_id)
        import requests
        r = requests.get(file.storage_url, timeout=30)
        r.raise_for_status()
        content = r.text
        chunks = [content[i:i+text_split] for i in range(0, len(content), text_split)]
        for i, ch in enumerate(chunks):
            KnowledgeChunk.objects.create(file=file, title=f"{file.filename}#{i+1}", content=ch)
        job.status = "done"
        job.save(update_fields=["status"])
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.save(update_fields=["status","error"])
        raise
