# from rest_framework import status
# from djoser.views import UserViewSet
# from rest_framework.response import Response
#
#
# class ActivationView(UserViewSet):
#     def activation(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.user
#         user.is_verified = True
#         user.save()
#         super().activation(request, *args, **kwargs)
#         return Response(
#             {"message": "Account activated successfully and verified!"},
#             status=status.HTTP_200_OK,
#         )
