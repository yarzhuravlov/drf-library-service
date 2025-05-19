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
    session_url = models.URLField()
    session_id = models.CharField(max_length=255)
    money_to_pay = models.PositiveBigIntegerField()
    status = models.CharField(max_length=10, choices=Statuses.choices)
    type = models.CharField(max_length=10, choices=Types.choices)
