from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from base.managers import UserManager
from base.models import TimestampedBaseModel


class User(TimestampedBaseModel, AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    first_name = models.CharField(max_length=63, blank=True)
    last_name = models.CharField(max_length=63, blank=True)
    phone_number = PhoneNumberField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
