from rest_framework.permissions import IsAuthenticated

from base.mixins import ListModelMixin, RetrieveModelMixin
from base.viewsets import GenericViewSet
from payments.models import Payment
from payments.serializers import PaymentSerializer


class PaymentViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Payment.objects.all()

    request_serializer_class = PaymentSerializer
    response_serializer_class = PaymentSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset

        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)

        return queryset
