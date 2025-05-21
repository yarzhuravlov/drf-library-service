from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, generics
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

import stripe

from base.mixins import ListModelMixin, RetrieveModelMixin
from base.viewsets import GenericViewSet
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import (
    update_payment_by_session_id,
    renew_payment_session,
    create_payment,
)
from borrowings.models import Borrowing
from notifications.handlers import send_notification_to_all_admin_users


@api_view(['POST'])
@extend_schema(
    summary="Handle Stripe webhooks",
    description="Endpoint for handling Stripe webhook events",
    responses={200: None},
)
def stripe_webhook(request):
    """Handle Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        update_payment_by_session_id(session.id)

    return Response(status=status.HTTP_200_OK)


class PaymentViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    """ViewSet for managing payments.

    This viewset provides endpoints for:
    * Listing payments (staff can see all, users see only their own)
    * Retrieving payment details
    * Handling successful payments
    * Handling cancelled payments
    * Creating payments for borrowings
    """

    queryset = Payment.objects.all()
    request_serializer_class = PaymentSerializer
    response_serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    action_permission_classes = {
        "list": IsAuthenticated,
        "retrieve": IsAuthenticated,
        "success": AllowAny,
        "cancel": AllowAny,
        "create_for_borrowing": IsAuthenticated,
    }

    def get_queryset(self):
        """Filter queryset based on user permissions.

        Staff users can see all payments, regular users see only their own.
        """
        queryset = self.queryset

        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)

        return queryset

    @extend_schema(
        summary="Handle successful payment",
        description=(
            "Endpoint for handling successful Stripe payment completion. "
            "Updates payment status to PAID if the session is valid and paid."
        ),
        parameters=[
            OpenApiParameter(
                name="session_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Stripe session ID",
                required=True,
            ),
        ],
        responses={
            200: {"description": "Payment status changed to PAID"},
            400: {"description": "session_id is required"},
            404: {"description": (
                "Paid session with such session_id not found"
            )},
        },
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="success",
        permission_classes=[AllowAny],
    )
    def success(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"detail": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = update_payment_by_session_id(session_id)

        if not payment:
            return Response(
                {"detail": "Paid session with such session_id not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not hasattr(payment, "borrowing"):
            return Response(
                {"detail": "Internal error: payment object is invalid."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        message = (
            f"💰 <b>Success</b>\n"
            f"ID: {payment.id}\n"
            f"Amount: {payment.money_to_pay}\n"
            f"User: {payment.borrowing.user.email}\n"
            f"Date: {payment.borrowing.borrow_date.strftime('%Y-%m-%d')}"
        )

        send_notification_to_all_admin_users(message)

        return Response({"message": "Payment status changed to PAID"})

    @extend_schema(
        summary="Handle cancelled payment",
        description=(
            "Endpoint for handling cancelled Stripe payment. "
            "Returns a message that payment can be completed later."
        ),
        responses={
            200: {"description": "Payment can be completed later"},
        },
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="cancel",
        permission_classes=[AllowAny],
    )
    def cancel(self, *args, **kwargs):
        return Response({"message": "Payment can be completed later"})

    @extend_schema(
        summary="Create payment for borrowing",
        description=(
            "Creates a new payment for a borrowing. "
            "Returns the payment details with Stripe checkout URL."
        ),
        responses={
            201: PaymentSerializer,
            400: {"description": (
                "Invalid borrowing ID or payment already exists"
            )},
            404: {"description": "Borrowing not found"},
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="create-for-borrowing/(?P<borrowing_id>[^/.]+)",
    )
    def create_for_borrowing(self, request, borrowing_id=None):
        """Create a new payment for a borrowing."""
        try:
            borrowing = Borrowing.objects.get(id=borrowing_id)
        except Borrowing.DoesNotExist:
            return Response(
                {"detail": "Borrowing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if borrowing.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Not authorized to create payment for this borrowing"},  # noqa: E501
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if payment already exists
        existing_payment = Payment.objects.filter(
            borrowing=borrowing,
            type=Payment.Types.PAYMENT,
        ).first()

        if existing_payment and existing_payment.status == Payment.Statuses.PAID:  # noqa: E501
            return Response(
                {
                    "detail": (
                        "Payment already completed for this borrowing"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if existing_payment and existing_payment.status == Payment.Statuses.PENDING:  # noqa: E501
            return Response(
                {
                    "detail": (
                        "Pending payment already exists for this borrowing"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = create_payment(borrowing, request)
            serializer = self.get_serializer(payment)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class RenewPaymentView(generics.UpdateAPIView):
    """Endpoint for renewing expired payment session.

    Allows users to renew their expired payment sessions to get a new
    Stripe checkout URL. Only the payment owner can renew their payment.
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Renew expired payment session",
        description=(
            "Creates a new Stripe session for an expired payment. "
            "Only the payment owner can renew their payment."
        ),
        responses={
            200: PaymentSerializer,
            403: {"description": "Not authorized to renew this payment."},
        },
    )
    def update(self, request, *args, **kwargs):
        payment = self.get_object()

        if payment.borrowing.user != request.user:
            return Response(
                {"detail": "Not authorized to renew this payment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payment = renew_payment_session(payment, request)
        serializer = self.get_serializer(payment)

        return Response(serializer.data)
