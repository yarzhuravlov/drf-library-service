from rest_framework.routers import DefaultRouter
from books.views import BookViewSet, AuthorViewSet


app_name = "books"

router = DefaultRouter()
router.register("books", BookViewSet)
router.register("authors", AuthorViewSet)


urlpatterns = router.urls
