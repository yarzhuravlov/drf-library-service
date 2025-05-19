from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingRetrieveSerializer,
)


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = self.queryset
        else:
            queryset = self.queryset.filter(user=user)

        is_active_param = self.request.query_params.get("is_active")
        user_id_param = self.request.query_params.get("user_id")

        if user.is_staff and user_id_param:
            queryset = self.queryset.filter(user__id=user_id_param)

        if is_active_param is not None:
            if is_active_param.lower() == "true":
                queryset = queryset.filter(actual_return__isnull=True)
            elif is_active_param.lower() == "false":
                queryset = queryset.filter(actual_return__isnull=False)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        if self.action == "retrieve":
            return BorrowingRetrieveSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)
