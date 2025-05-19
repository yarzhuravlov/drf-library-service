from django.db import models


class Author(models.Model):
    first_name = models.CharField(max_length=63)
    last_name = models.CharField(max_length=63)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Book(models.Model):
    class Covers(models.TextChoices):
        HARD = "hard"
        SOFT = "soft"

    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(
        Author,
        related_name="books",
    )
    cover = models.CharField(max_length=4, choices=Covers.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.PositiveIntegerField()

    def __str__(self):
        return self.title
