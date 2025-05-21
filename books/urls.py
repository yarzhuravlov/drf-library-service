from rest_framework.routers import DefaultRouter
from books.views import BookViewSet, AuthorViewSet


app_name = "books"

router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")
router.register(r"authors", AuthorViewSet, basename="author")

urlpatterns = router.urls
