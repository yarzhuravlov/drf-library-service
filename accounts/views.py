from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.test import APIRequestFactory
from rest_framework import status
from djoser.views import UserViewSet
from rest_framework.response import Response


@csrf_exempt
def activate_user(request, uid, token):
    """
    Activate user account by GET request using uid and token from the activation link.
    """
    if request.method == "GET":
        # Simulate a POST request to Djoser's activation endpoint
        factory = APIRequestFactory()
        post_request = factory.post(
            "/api/v1/auth/users/activation/",
            {"uid": uid, "token": token},
            format="json"
        )
        view = UserViewSet.as_view({"post": "activation"})
        response = view(post_request)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            return HttpResponse(
                "Your account has been activated! You can now log in.",
                status=200
            )
        else:
            return HttpResponse(
                "Activation failed. "
                "The link is invalid or has already been used.",
                status=400
            )
    return HttpResponse("Method not allowed", status=405)


class ActivationView(UserViewSet):
    def activation(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        user.is_verified = True
        user.save()
        super().activation(request, *args, **kwargs)
        return Response(
            {"message": "Account activated successfully and verified!"},
            status=status.HTTP_200_OK,
        )
