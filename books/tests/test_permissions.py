from django.test import TestCase
from books.models import Book
from books.serializers import BookSerializer
from books.models import Author


class BookSerializerTest(TestCase):
    def setUp(self):
        self.valid_author = Author.objects.create(first_name="John", last_name="Doe")

    def test_book_must_have_at_least_one_author(self):
        data = {
            "title": "Test Book",
            "author_ids": [],
            "cover": Book.Covers.HARD,
            "inventory": 10,
            "daily_fee": 5,
        }
        serializer = BookSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("author_ids", serializer.errors)
        self.assertEqual(
            serializer.errors["author_ids"][0],
            "Book must have at least one author."
        )

    def test_book_with_authors_is_valid(self):
        data = {
            "title": "Valid Book",
            "author_ids": [self.valid_author.id],
            "cover": Book.Covers.SOFT,
            "inventory": 5,
            "daily_fee": 3,
        }
        serializer = BookSerializer(data=data)
        self.assertTrue(serializer.is_valid())
