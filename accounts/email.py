from django.conf import settings
from djoser.email import ActivationEmail as DjoserActivationEmail


class ActivationEmail(DjoserActivationEmail):
    template_name = "email/activation_email.html"

    def get_context_data(self):
        context = super().get_context_data()
        rel_url = context.get("url", "").lstrip("/")
        context["activation_url"] = (
            f"{settings.FRONTEND_PROTOCOL}://"
            f"{settings.FRONTEND_DOMAIN}/{rel_url}"
        )
        return context
