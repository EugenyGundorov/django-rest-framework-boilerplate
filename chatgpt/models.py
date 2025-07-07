from django.db import models

class GPTRequest(models.Model):
    request_id    = models.CharField(max_length=100, unique=True)
    client_id     = models.CharField(max_length=100)
    system_prompt = models.TextField()
    user_message  = models.TextField()
    model         = models.CharField(max_length=50)
    response_text = models.TextField(null=True, blank=True)
    completed     = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request_id} – {'done' if self.completed else 'pending'}"