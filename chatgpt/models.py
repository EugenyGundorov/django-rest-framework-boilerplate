
from django.db import models

class GPTRequest(models.Model):
    request_id    = models.CharField(max_length=100, unique=True)
    gpt_api       = models.CharField(max_length=100, default='openai')  # openai|grok|custom
    client_id     = models.CharField(max_length=100, db_index=True)
    system_prompt = models.TextField(blank=True, default="")
    assist_promt  = models.TextField(blank=True, default="")  # legacy
    assyst_promt  = models.TextField(blank=True, default="")  # agent prompt
    user_message  = models.TextField(blank=True, default="")
    model         = models.CharField(max_length=100, blank=True, default="gpt-4o-mini")
    gpt_key       = models.CharField(max_length=200, blank=True, default="")
    agent_key     = models.CharField(max_length=200, blank=True, default="")  # ключ агента
    message_size  = models.IntegerField(default=2048)
    use_agent     = models.BooleanField(default=False)
    files         = models.JSONField(default=list, blank=True)      # list of URLs or ids
    knowledge     = models.JSONField(default=list, blank=True)      # list of {title, content}
    response_text = models.TextField(null=True, blank=True)
    completed     = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["client_id", "created_at"]),
            models.Index(fields=["completed", "created_at"]),
        ]

    def __str__(self):
        return f"{self.request_id} ({self.client_id})"
