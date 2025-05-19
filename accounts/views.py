from dj_rest_auth.registration.views import ConfirmEmailView

class CustomConfirmEmailView(ConfirmEmailView):
    template_name = "account/email/email_confirm.html"
