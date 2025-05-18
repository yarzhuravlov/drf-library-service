from django.db import models


class Author(models.Model):
    first_name = models.CharField(max_length=63)
    last_name = models.CharField(max_length=63)


class Book(models.Model):
    class Covers(models.TextChoices):
        HARD = "hard"
        SOFT = "soft"

    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        Author,
        related_name="books",
        on_delete=models.PROTECT,
    )
    cover = models.CharField(max_length=4, choices=Covers.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.PositiveIntegerField()
