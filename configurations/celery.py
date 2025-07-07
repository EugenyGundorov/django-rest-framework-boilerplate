import os
from celery import Celery

# Устанавливаем переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')

app = Celery('configurations')

# Загружаем конфиги Celery из Django settings, префикс CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автопоиск задач в INSTALLED_APPS
app.autodiscover_tasks()