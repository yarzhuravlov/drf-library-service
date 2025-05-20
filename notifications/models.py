from django.conf import settings
from django.db import models


class TelegramUser(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_profile",
    )
    telegram_id = models.BigIntegerField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.user.email} (tg_id={self.telegram_id})"
