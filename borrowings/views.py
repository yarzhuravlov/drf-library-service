from rest_framework import viewsets

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingRetrieveSerializer,
)

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return BorrowingListSerializer
        if self.action == 'retrieve':
            return BorrowingRetrieveSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)
