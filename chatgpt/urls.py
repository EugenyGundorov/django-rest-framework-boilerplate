from django.urls import path
from .views import submit_request, check_status, get_result, health_check

urlpatterns = [
    path('submit/', submit_request, name='submit_request'),
    path('status/', check_status, name='check_status'),
    path('result/', get_result, name='get_result'),
    path('health/', health_check, name='health_check'),
]