from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from books.models import Book, Author
from books.permissions import IsAdminOrReadOnly
from books.serializers import BookSerializer, AuthorSerializer


@extend_schema(tags=["Authors"])
class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAdminOrReadOnly]


@extend_schema(tags=["Books"])
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrReadOnly]
