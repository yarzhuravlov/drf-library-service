from django.contrib.auth import get_user_model
from django.db import models
from rest_framework.exceptions import ValidationError

from books.models import Book

User = get_user_model()


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return = models.DateField()
    actual_return = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        default_related_name = "borrowings"

    # @property
    # def total_price(self):
    #     pass
    #
    # @property
    # def fine_price(self):
    #     pass

    def clean(self):
        if self.expected_return <= self.borrow_date:
            raise ValidationError(
                "Expected return date must be after borrow date."
            )
        if self.actual_return and self.actual_return <= self.borrow_date:
            raise ValidationError(
                "Actual return date cannot be before borrow date."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} took {self.book} {self.borrow_date}"
