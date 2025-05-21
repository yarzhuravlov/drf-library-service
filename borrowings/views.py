from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingRetrieveSerializer,
    BorrowingReturnSerializer,
)
from payments.models import Payment
from payments.services import create_payment


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
        if self.action == "return_borrowing":
            return BorrowingReturnSerializer
        return BorrowingSerializer

    @action(
        detail=True,
        methods=["post"],
        serializer_class=BorrowingReturnSerializer,
    )
    def return_borrowing(self, request, pk=None):
        if not request.user.is_staff:
            return Response(
                {"detail:" "Only admin can return borrowings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        borrowing = self.get_object()
        serializer = self.get_serializer(instance=borrowing, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Book returned successfully."})

    def perform_create(self, serializer):
        user = self.request.user

        pending_exists = Payment.objects.filter(
            borrowing__user=user, status=Payment.Statuses.PENDING
        ).exists()

        if pending_exists:
            raise ValidationError(
                {
                    "detail": "You have pending payments. Please settle them before borrowing another book."  # noqa: E501
                }
            )

        with transaction.atomic():
            borrowing = serializer.save(user=user)
            create_payment(borrowing, self.request)
        return borrowing
