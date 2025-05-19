from django.contrib.auth import get_user_model
from django.db import models

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
