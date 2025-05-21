from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
)
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

    @extend_schema(
        summary="List all borrowings",
        description=(
            f"Returns a list of borrowings."
            f" Non-staff users see only their own borrowings. "
            f"Staff users can filter by user_id"
            f" or is_active status (true for active, false for returned)."
        ),
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by active (true) or returned (false) borrowings.",
                enum=["true", "false"],
            ),
            OpenApiParameter(
                name="user_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter by user ID (staff only).",
            ),
        ],
        responses={
            200: BorrowingListSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new borrowing",
        description=(
            f"Creates a new borrowing for an authenticated user. "
            f"Requires book ID and borrow date."
            f" Checks for pending payments and decreases book inventory."
        ),
        request=BorrowingSerializer,
        responses={
            201: BorrowingSerializer,
            400: OpenApiResponse(
                description="Invalid data or book unavailable"
            ),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Pending payments detected"),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve borrowing details",
        description=f"Returns detailed information"
                    f" about a specific borrowing by ID.",
        responses={
            200: BorrowingRetrieveSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Borrowing not found"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update borrowing",
        description=(
            "Updates all fields of a borrowing. "
            f"Accessible only to staff users."
            f" Typically used to modify borrow or return dates."
        ),
        request=BorrowingSerializer,
        responses={
            200: BorrowingSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden for non-staff"),
            404: OpenApiResponse(description="Borrowing not found"),
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update borrowing",
        description=(
            "Updates specific fields of a borrowing. "
            "Accessible only to staff users."
        ),
        request=BorrowingSerializer,
        responses={
            200: BorrowingSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden for non-staff"),
            404: OpenApiResponse(description="Borrowing not found"),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete borrowing",
        description="Deletes a borrowing by ID. Accessible only to staff users.",
        responses={
            204: OpenApiResponse(description="Borrowing deleted"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden for non-staff"),
            404: OpenApiResponse(description="Borrowing not found"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Return a borrowed book",
        description=(
            f"Marks a borrowing as returned,"
            f" updates book inventory,"
            f" and creates a fine payment if overdue. "
            "Accessible only to staff users."
        ),
        request=BorrowingReturnSerializer,
        responses={
            200: OpenApiResponse(description="Book returned successfully"),
            400: OpenApiResponse(description="Borrowing already returned"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden for non-staff"),
            404: OpenApiResponse(description="Borrowing not found"),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        serializer_class=BorrowingReturnSerializer,
    )
    def return_borrowing(self, request, pk=None):
        if not request.user.is_staff:
            return Response(
                {"detail": "Only admin can return borrowings."},
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
                    "detail": f"You have pending payments."
                              f" Please settle them"
                              f" before borrowing another book."
                }
            )

        with transaction.atomic():
            borrowing = serializer.save(user=user)
            create_payment(borrowing, self.request)
        return borrowing
