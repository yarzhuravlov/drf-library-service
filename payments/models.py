from django.db import models
from django.utils import timezone

from borrowings.models import Borrowing


class Payment(models.Model):
    class Statuses(models.TextChoices):
        PENDING = "pending"
        PAID = "paid"
        EXPIRED = "expired"

    class Types(models.TextChoices):
        PAYMENT = "payment"
        FINE = "fine"

    borrowing = models.ForeignKey(
        Borrowing,
        related_name="payments",
        on_delete=models.PROTECT,
    )
    session_url = models.URLField(unique=True)
    session_id = models.CharField(max_length=255, unique=True)
    money_to_pay = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=10,
        choices=Statuses.choices,
        default=Statuses.PENDING,
    )
    type = models.CharField(max_length=10, choices=Types.choices)
    expiration_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Payment by {self.borrowing.user.email}."

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "borrowing",
                "type",
                name="unique_type_borrowing",
            )
        ]

    def is_expired(self) -> bool:
        """Check if payment session is expired based on expiration_at field."""
        return self.expiration_at <= timezone.now()
