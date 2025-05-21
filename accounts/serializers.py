from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers
from datetime import date


class UserSerializer(DjoserUserSerializer):
    class Meta(DjoserUserSerializer.Meta):
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "date_of_birth",
        )

    def validate_date_of_birth(self, value):
        today = date.today()
        if value > today:
            raise serializers.ValidationError(
                "Date of birth cannot be in the future."
            )
        min_age = 10
        age = today.year - value.year - (
            (today.month, today.day) < (value.month, value.day)
        )
        if age < min_age:
            raise serializers.ValidationError(
                "User must be at least 10 years old."
            )
        return value
