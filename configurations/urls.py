from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest')),
    path('api/token/',         TokenObtainPairView.as_view(),   name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    path('user/', include(('app_dir.user.urls', 'user'), namespace='user')),
    path('api/user/', include(('app_dir.user.api.urls', 'user_api'), namespace='user_api')),
    path('api/module/', include(('app_dir.module.api.urls', 'module_api'), namespace='module_api')),
    path('api/', include(('chatgpt.urls', 'chatgpt'), namespace='chatgpt')),
]

