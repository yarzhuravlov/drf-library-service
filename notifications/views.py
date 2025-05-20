from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import IntegrityError
from notifications.models import TelegramUser

User = get_user_model()


class RegisterTelegramUserWithJWTView(APIView):
    """
    Accepts POST with email, password, telegram_id.
    Authenticates, links Telegram, returns JWT tokens.
    """

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        telegram_id = request.data.get("telegram_id")

        if not (email and password and telegram_id):
            return Response(
                {"error": "Email, password and telegram_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {"error": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check telegram_id uniqueness
        existing = (
            TelegramUser.objects.filter(telegram_id=telegram_id)
            .exclude(user=user)
            .first()
        )
        if existing:
            return Response(
                {"error": "This telegram_id is already in use"},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            TelegramUser.objects.update_or_create(
                user=user,
                defaults={"telegram_id": telegram_id},
            )
        except IntegrityError:
            return Response(
                {"error": "This telegram_id is already in use."},
                status=status.HTTP_409_CONFLICT,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
