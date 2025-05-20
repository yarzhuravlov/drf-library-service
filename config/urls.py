"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("dj_rest_auth.urls")),
    path(
        "api/v1/auth/registration/", include("dj_rest_auth.registration.urls")
    ),
    path(
        "api/v1/auth/jwt/token/",
        TokenObtainPairView.as_view(),
        name="jwt-token",
    ),
    path(
        "api/v1/auth/jwt/refresh/",
        TokenRefreshView.as_view(),
        name="jwt-refresh",
    ),
    path(
        "api/v1/auth/jwt/verify/", TokenVerifyView.as_view(), name="jwt-verify"
    ),
    path("api/v1/books/", include("books.urls")),
    path("api/v1/", include("borrowings.urls")),
    path("api/v1/", include("payments.urls")),
    path("api/v1/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += debug_toolbar_urls()
