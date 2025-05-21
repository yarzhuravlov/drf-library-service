from djoser.email import ActivationEmail as DjoserActivationEmail


class ActivationEmail(DjoserActivationEmail):
    template_name = "email/activation_email.html"

    def get_context_data(self):
        context = super().get_context_data()
        context["activation_url"] = context.get("url", "")
        return context
