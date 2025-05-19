import json
from django.test import TestCase, Client
from django.urls import reverse
from books.models import Author, Book
from django.contrib.auth import get_user_model

User = get_user_model()

class BookViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email="admin@example.com", password="admin123", is_staff=True
        )
        self.user = User.objects.create_user(
            email="user@example.com", password="user123", is_staff=False
        )
        self.author = Author.objects.create(first_name="Mark", last_name="Twain")

    def test_list_books_unauthenticated(self):
        url = reverse("books:book-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_create_book(self):
        self.client.login(email="admin@example.com", password="admin123")
        url = reverse("books:book-list")
        data = {
            "title": "Tom Sawyer",
            "author_ids": [self.author.id],
            "inventory": 5,
            "daily_fee": 3,
            "cover": "hard",
        }
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

    def test_user_cannot_create_book(self):
        self.client.login(email="user@example.com", password="user123")
        url = reverse("books:book-list")
        data = {
            "title": "Tom Sawyer",
            "author_ids": [self.author.id],
            "inventory": 5,
            "daily_fee": 3,
            "cover": "hard",
        }
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_get_book_detail(self):
        book = Book.objects.create(
            title="Tom Sawyer",
            inventory=5,
            daily_fee=3,
            cover="hard"
        )
        book.authors.set([self.author])
        url = reverse("books:book-detail", args=[book.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Tom Sawyer")
        self.assertIn("authors", response.data)

    def test_admin_can_update_book(self):
        book = Book.objects.create(
            title="Old Title",
            inventory=5,
            daily_fee=3,
            cover="soft"
        )
        book.authors.set([self.author])
        self.client.login(email="admin@example.com", password="admin123")
        url = reverse("books:book-detail", args=[book.id])
        data = {
            "title": "New Title",
            "author_ids": [self.author.id],
            "inventory": 10,
            "daily_fee": 5,
            "cover": "hard",
        }
        response = self.client.put(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        book.refresh_from_db()
        self.assertEqual(book.title, "New Title")
        self.assertEqual(book.inventory, 10)

    def test_user_cannot_update_book(self):
        book = Book.objects.create(
            title="Old Title",
            inventory=5,
            daily_fee=3,
            cover="soft"
        )
        book.authors.set([self.author])
        self.client.login(email="user@example.com", password="user123")
        url = reverse("books:book-detail", args=[book.id])
        data = {
            "title": "New Title",
            "author_ids": [self.author.id],
            "inventory": 10,
            "daily_fee": 5,
            "cover": "hard",
        }
        response = self.client.put(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_delete_book(self):
        book = Book.objects.create(
            title="To Delete",
            inventory=5,
            daily_fee=3,
            cover="hard"
        )
        book.authors.set([self.author])
        self.client.login(email="admin@example.com", password="admin123")
        url = reverse("books:book-detail", args=[book.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Book.objects.filter(id=book.id).exists())

    def test_user_cannot_delete_book(self):
        book = Book.objects.create(
            title="To Delete",
            inventory=5,
            daily_fee=3,
            cover="hard"
        )
        book.authors.set([self.author])
        self.client.login(email="user@example.com", password="user123")
        url = reverse("books:book-detail", args=[book.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
