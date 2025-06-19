from django.db import transaction
from django.utils.timezone import localdate
from rest_framework import serializers
from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from payments.services import create_fine_payment
from payments.serializers import PaymentSerializer


class BorrowingSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), help_text="ID of the book to borrow."
    )
    payments = PaymentSerializer(
        many=True,
        read_only=True,
        help_text="List of payments associated with this borrowing.",
    )
    borrow_date = serializers.DateField(
        help_text="Date when the book was borrowed."
    )
    expected_return = serializers.DateField(
        help_text="Expected return date of the book."
    )
    actual_return = serializers.DateField(
        read_only=True,
        help_text="Actual return date of the book (null if not returned).",
    )

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return",
            "book",
            "payments",
        )
        read_only_fields = ("id", "user", "actual_return")

    def validate_book(self, book):
        if book.inventory < 1:
            raise serializers.ValidationError(
                "This book is currently not available for borrowing."
            )
        return book

    def create(self, validated_data):
        with transaction.atomic():
            book = validated_data["book"]
            book.inventory -= 1
            book.save()
            borrowing = super().create(validated_data)
        return borrowing


class BorrowingListSerializer(serializers.ModelSerializer):
    book = serializers.SlugRelatedField(
        slug_field="title",
        many=False,
        read_only=True,
        help_text="Title of the borrowed book.",
    )
    borrow_date = serializers.DateField(
        help_text="Date when the book was borrowed."
    )
    expected_return = serializers.DateField(
        help_text="Expected return date of the book."
    )
    actual_return = serializers.DateField(
        help_text="Actual return date of the book (null if not returned)."
    )

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return",
            "book",
        )


class BorrowingRetrieveSerializer(BorrowingSerializer):
    book = BookSerializer(
        read_only=True,
        help_text="Detailed information about the borrowed book.",
    )
    user = serializers.SlugRelatedField(
        slug_field="email",
        read_only=True,
        help_text="Email of the user who borrowed the book.",
    )

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "user",
            "book",
            "borrow_date",
            "expected_return",
            "actual_return",
        )


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ()  # No fields required in request

    def validate(self, data):
        if self.instance.actual_return:
            raise serializers.ValidationError(
                "This borrowing is already returned."
            )
        return data

    def update(self, instance, validated_data):
        with transaction.atomic():
            today = localdate()
            instance.actual_return = today
            instance.book.inventory += 1
            instance.book.save()
            instance.save()

            if today > instance.expected_return:
                request = self.context.get("request")
                create_fine_payment(instance, request)

        return instance
