from django.urls import path
from notifications.views import RegisterTelegramUserWithJWTView

urlpatterns = [
    path(
        "bots/register_user/",
        RegisterTelegramUserWithJWTView.as_view(),
        name="register_telegram_user",
    ),
]
