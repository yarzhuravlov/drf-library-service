from rest_framework import status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from base.mixins import ListModelMixin, RetrieveModelMixin
from base.viewsets import GenericViewSet
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import (
    update_payment_by_session_id,
    renew_payment_session,
)
from notifications.handlers import send_notification_to_all_admin_users


class PaymentViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Payment.objects.all()
    request_serializer_class = PaymentSerializer
    response_serializer_class = PaymentSerializer

    action_permission_classes = {
        "list": IsAuthenticated,
        "retrieve": IsAuthenticated,
        "success": AllowAny,
        "cancel": AllowAny,
    }

    def get_queryset(self):
        queryset = self.queryset

        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)

        return queryset

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

        message = (
            f"💰 <b>Success</b>\n"
            f"ID: {payment.id}\n"
            f"Amount: {payment.money_to_pay}\n"
            f"User: {payment.borrowing.user.email}\n"
            f"Date: {payment.borrowing.borrow_date.strftime('%Y-%m-%d')}"
        )

        send_notification_to_all_admin_users(message)

        return Response({"message": "Payment status changed to PAID"})

    @action(
        detail=False,
        methods=["get"],
        url_path="cancel",
        permission_classes=[AllowAny],
    )
    def cancel(self, *args, **kwargs):
        return Response({"message": "Payment can be completed later"})


class RenewPaymentView(generics.UpdateAPIView):
    """Endpoint for renewing expired payment session."""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

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
