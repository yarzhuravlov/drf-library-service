from base.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from accounts.serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer
)

User = get_user_model()

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    action_serializers = {
        "list": UserListSerializer,
        "retrieve": UserDetailSerializer,
        "create": UserCreateSerializer,
        "update": UserCreateSerializer,
        "partial_update": UserCreateSerializer,
    }
    action_permissions = {
        "create": [IsAdminUser],
        "update": [IsAdminUser],
        "partial_update": [IsAdminUser],
        "destroy": [IsAdminUser],
        "list": [IsAdminUser],
        "retrieve": [IsAdminUser],
    }
    request_action_serializer_classes = {
        "create": UserCreateSerializer,
        "update": UserCreateSerializer,
        "partial_update": UserCreateSerializer,
    }
    response_action_serializer_classes = {
        "list": UserListSerializer,
        "retrieve": UserDetailSerializer,
        "create": UserDetailSerializer,
        "update": UserDetailSerializer,
        "partial_update": UserDetailSerializer,
    }
