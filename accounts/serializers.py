from djoser.serializers import UserSerializer as DjoserUserSerializer


class UserSerializer(DjoserUserSerializer):
    class Meta(DjoserUserSerializer.Meta):
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "date_of_birth",
        )
