import os

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.contrib.sites.models import Site
        from django.conf import settings

        Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={
                "domain": os.getenv("SITE_DOMAIN", "127.0.0.1:8000"),
                "name": os.getenv("SITE_NAME", "ReadRiot"),
            }
        )