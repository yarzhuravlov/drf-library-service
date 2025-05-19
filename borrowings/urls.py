from django.urls import path, include
from rest_framework.routers import DefaultRouter
from borrowings.views import BorrowingViewSet


app_name = "borrowings"

router = DefaultRouter()
router.register("borrowings", BorrowingViewSet, basename="borrowing")

urlpatterns = router.urls
