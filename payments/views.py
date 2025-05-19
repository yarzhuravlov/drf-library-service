from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from base.mixins import ListModelMixin, RetrieveModelMixin
from base.viewsets import GenericViewSet
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import update_payment_by_session_id


class PaymentViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Payment.objects.all()

    request_serializer_class = PaymentSerializer
    response_serializer_class = PaymentSerializer

    # permission_classes = [IsAuthenticated]

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
        session_id = self.request.GET.get("session_id")

        if not session_id:
            return Response(
                "session_id is required",
                status.HTTP_400_BAD_REQUEST,
            )

        payment = update_payment_by_session_id(session_id)

        if payment:
            return Response("Payment status changed to PAID")

        return Response(
            "Paid session with such session_id not found",
            status.HTTP_404_NOT_FOUND,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="cancel",
        permission_classes=[AllowAny],
    )
    def cancel(self, *args, **kwargs):
        return Response("Payment can be completed later")
