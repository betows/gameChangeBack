from django.contrib import admin
from .views import CustomLoginView
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('tasks.urls')),
    path('api/authentication/', include('authentication.urls')),
    path('api/authentication/', include('users.urls')),
    path('dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
    path('dj-rest-auth/socialaccounts/', include('allauth.socialaccount.urls')),
    path('api/login', CustomLoginView.as_view(), name='custom_login'),
    # Include other app URLs as needed
]
