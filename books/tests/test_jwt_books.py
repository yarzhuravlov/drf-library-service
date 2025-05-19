import json
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from books.models import Author, Book

User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }

class JWTBookPermissionsTest(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="admin123",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="normaluser",
            email="user@example.com",
            password="user123",
            is_staff=False,
        )
        self.author = Author.objects.create(first_name="Mark", last_name="Twain")

        self.book_url = reverse("books:book-list")
        self.book_data = {
            "title": "Tom Sawyer",
            "author_ids": [self.author.id],
            "inventory": 5,
            "daily_fee": 3,
            "cover": "hard"
        }

    def test_admin_can_create_book_with_jwt(self):
        tokens = get_tokens_for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        response = self.client.post(
            self.book_url,
            data=json.dumps(self.book_data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

    def test_user_cannot_create_book_with_jwt(self):
        tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        response = self.client.post(
            self.book_url,
            data=json.dumps(self.book_data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_create_book(self):
        response = self.client.post(
            self.book_url,
            data=json.dumps(self.book_data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_admin_can_update_book(self):
        book = Book.objects.create(
            title="Old Title",
            inventory=3,
            daily_fee=2,
            cover="soft"
        )
        book.authors.add(self.author)

        tokens = get_tokens_for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])

        url = reverse("books:book-detail", args=[book.id])
        updated_data = {
            "title": "New Title",
            "author_ids": [self.author.id],
            "inventory": 10,
            "daily_fee": 4,
            "cover": "hard"
        }

        response = self.client.put(
            url,
            data=json.dumps(updated_data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "New Title")

    def test_admin_can_delete_book(self):
        book = Book.objects.create(
            title="To Delete",
            inventory=1,
            daily_fee=1,
            cover="soft"
        )
        book.authors.add(self.author)

        tokens = get_tokens_for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])

        url = reverse("books:book-detail", args=[book.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Book.objects.filter(id=book.id).exists())
