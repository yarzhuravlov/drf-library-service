from typing import Dict, Iterable, Optional, Type, Union

from django.core.exceptions import ImproperlyConfigured
from rest_framework import viewsets
from rest_framework.permissions import BasePermission
from rest_framework.serializers import BaseSerializer

from base.generics import GenericAPIView
from base.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)


class GenericViewSet(viewsets.ViewSetMixin, GenericAPIView):
    action_permission_classes: Optional[
        Dict[str, Union[Type[BasePermission], Iterable[Type[BasePermission]]]]
    ] = None
    request_action_serializer_classes: Optional[
        Dict[str, Type[BaseSerializer]]
    ] = None
    response_action_serializer_classes: Optional[
        Dict[str, Type[BaseSerializer]]
    ] = None

    def get_permission_classes_or_none(self):
        return map_action_to_classes(self, "action_permission_classes")

    def get_permissions(self):
        permissions = []

        permission_classes = self.get_permission_classes_or_none()

        if permission_classes is not None:

            if isinstance(permission_classes, Iterable):
                for permission_class in permission_classes:
                    permissions.append(permission_class())
            else:
                permissions.append(permission_classes())

        return permissions or super().get_permissions()

    def get_request_serializer_class_or_none(
        self,
    ) -> Optional[Type[BaseSerializer]]:
        serializer_class = map_action_to_classes(
            self, "request_action_serializer_classes"
        )

        if serializer_class is None:
            return super().get_request_serializer_class_or_none()

        return serializer_class

    def raise_request_serializer_error(self):
        raise ImproperlyConfigured(
            f"{self.__class__.__name__} should properly configure "
            "`request_action_serializer_classes` attribute"
        )

    def get_response_serializer_class_or_none(
        self,
    ) -> Optional[Type[BaseSerializer]]:
        serializer_class = map_action_to_classes(
            self, "response_action_serializer_classes"
        )

        if serializer_class is None:
            return super().get_response_serializer_class_or_none()

        return serializer_class

    def raise_response_serializer_error(self):
        raise ImproperlyConfigured(
            f"{self.__class__.__name__} should properly configure "
            "`response_action_serializer_classes` attribute"
        )

    def raise_serializer_error(self):
        raise ImproperlyConfigured(
            f"{self.__class__.__name__} should properly "
            f"configure one of these attributes: "
            f"`response_action_serializer_classes`, `serializer_class`"
        )


def map_action_to_classes(view: GenericViewSet, action_classes_arg_name: str):
    if hasattr(view, action_classes_arg_name) and (
        action_classes := getattr(view, action_classes_arg_name)
    ):
        classes = action_classes.get(view.action)

        if classes is None and view.action == "partial_update":
            classes = action_classes.get(view.action)

        return classes

    return None


class ReadOnlyModelViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    """
    A viewset that provides default `list()` and `retrieve()` actions.
    """

    pass


class ModelViewSet(
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, `destroy()` and `list()` actions.
    """

    pass
