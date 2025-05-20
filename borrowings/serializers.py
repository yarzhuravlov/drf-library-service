from django.utils.timezone import localdate
from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from payments.services import create_fine_payment
from payments.serializers import PaymentSerializer


class BorrowingSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    payments = PaymentSerializer(many=True, read_only=True)

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
        book = validated_data["book"]
        book.inventory -= 1
        book.save()
        return super().create(validated_data)


class BorrowingListSerializer(serializers.ModelSerializer):
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
    book = BookSerializer(read_only=True)

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
        fields = ()

    def validate(self, data):
        if self.instance.actual_return:
            raise serializers.ValidationError(
                "This borrowing is already returned."
            )
        return data

    def update(self, instance, validated_data):
        today = localdate()
        instance.actual_return = today
        instance.book.inventory += 1
        instance.book.save()
        instance.save()

        if today > instance.expected_return:
            request = self.context.get("request")
            create_fine_payment(instance, request)

        return instance
