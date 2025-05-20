from django.urls import path
from rest_framework.routers import DefaultRouter

from payments.views import PaymentViewSet, RenewPaymentView

app_name = "payments"

router = DefaultRouter()
router.register("payments", PaymentViewSet)

urlpatterns = [
    path(
        "payments/<int:pk>/renew/",
        RenewPaymentView.as_view(),
        name="payment-renew"
    ),
    path(
        "payments/success/",
        PaymentViewSet.as_view({"get": "success"}),
        name="payment-success",
    ),
    path(
        "payments/cancel/",
        PaymentViewSet.as_view({"get": "cancel"}),
        name="payment-cancel",
    ),
]

urlpatterns += router.urls
