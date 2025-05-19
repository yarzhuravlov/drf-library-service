from rest_framework.routers import DefaultRouter

from payments.views import PaymentViewSet

app_name = "payments"

router = DefaultRouter()
router.register("payments", PaymentViewSet)


urlpatterns = router.urls
