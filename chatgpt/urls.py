
from django.urls import path
from .views import SubmitView, StatusView, ResultView, CleanupView, HealthView

urlpatterns = [
    path('submit/', SubmitView.as_view(), name='submit_request'),
    path('status/', StatusView.as_view(), name='check_status'),
    path('result/', ResultView.as_view(), name='get_result'),
    path('cleanup/', CleanupView.as_view(), name='cleanup_requests'),
    path('health/', HealthView.as_view(), name='health_check'),
]
