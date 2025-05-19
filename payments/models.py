from django.db import models

from borrowings.models import Borrowing


class Payment(models.Model):
    class Statuses(models.TextChoices):
        PENDING = "pending"
        PAID = "paid"

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
