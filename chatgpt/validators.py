
import httpx
from django.conf import settings

class FileValidationError(Exception):
    pass

async def validate_files(urls):
    if not urls:
        return
    max_bytes = settings.FILES_MAX_SIZE_MB * 1024 * 1024
    allowed = set([m.strip() for m in settings.FILES_ALLOWED_MIME])
    async with httpx.AsyncClient(timeout=15.0) as client:
        for u in urls:
            try:
                r = await client.head(u, follow_redirects=True)
                ctype = r.headers.get("Content-Type","").split(";")[0].strip()
                clen = int(r.headers.get("Content-Length","0"))
                if ctype and allowed and ctype not in allowed:
                    raise FileValidationError(f"Disallowed content-type: {ctype}")
                if clen and clen > max_bytes:
                    raise FileValidationError(f"File too large: {clen} bytes")
            except Exception as e:
                raise FileValidationError(str(e))
