from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions

User = get_user_model()


class ServiceWithUserAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        service_secret = request.META.get("HTTP_X_SERVICE_SECRET")
        if not service_secret:
            return None

        if (
            not settings.SERVICE_SECRETS
            or service_secret not in settings.SERVICE_SECRETS
        ):
            raise exceptions.AuthenticationFailed("Unknown service secret")

        user_id = request.META.get("HTTP_X_USER_ID")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("No such user")

        return (user, None)
