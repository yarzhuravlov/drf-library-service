from django.urls import path
from rest_framework.routers import DefaultRouter

from payments.views import (
    PaymentViewSet,
    RenewPaymentView,
    stripe_webhook,
)

app_name = "payments"

router = DefaultRouter()
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path(
        "success/",
        PaymentViewSet.as_view({"get": "success"}),
        name="payment-success",
    ),
    path(
        "cancel/",
        PaymentViewSet.as_view({"get": "cancel"}),
        name="payment-cancel",
    ),
    path(
        "<int:pk>/renew/",
        RenewPaymentView.as_view(),
        name="payment-renew",
    ),
    path(
        "webhook/",
        stripe_webhook,
        name="stripe-webhook",
    ),
]

urlpatterns += router.urls
