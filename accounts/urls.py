from django.urls import path
from accounts.views import ActivationView

app_name = "accounts"

urlpatterns = [
    path("accounts/activation/", ActivationView.as_view({"post": "activation"}), name="email-activation"),
]
