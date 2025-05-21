from rest_framework import serializers
from books.models import Author, Book


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ("id", "first_name", "last_name")


class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    author_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Author.objects.all(),
        write_only=True,
        source="authors",
    )

    class Meta:
        model = Book
        fields = (
            "id",
            "title",
            "authors",
            "author_ids",
            "cover",
            "inventory",
            "daily_fee",
        )

    def validate_author_ids(self, value):
        if not value:
            raise serializers.ValidationError(
                "Book must have at least one author."
            )
        return value
