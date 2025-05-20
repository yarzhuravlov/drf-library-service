from django.test import TestCase
from books.models import Author, Book

class AuthorModelTest(TestCase):
    def test_create_author(self):
        author = Author.objects.create(first_name="George", last_name="Orwell")
        self.assertEqual(str(author), "George Orwell")

class BookModelTest(TestCase):
    def setUp(self):
        self.author = Author.objects.create(first_name="Jane", last_name="Austen")

    def test_create_book(self):
        book = Book.objects.create(
            title="Pride and Prejudice",
            inventory=5,
            daily_fee=10,
            cover="soft"
        )
        book.authors.add(self.author)
        self.assertEqual(book.title, "Pride and Prejudice")
        self.assertIn(self.author, book.authors.all())

    def test_book_str(self):
        book = Book.objects.create(
            title="Emma",
            inventory=2,
            daily_fee=7,
            cover="hard"
        )
        self.assertEqual(str(book), "Emma")

    def test_author_str(self):
        author = Author.objects.create(first_name="Leo", last_name="Tolstoy")
        self.assertEqual(str(author), "Leo Tolstoy")
