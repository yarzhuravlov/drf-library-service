from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from rest_framework.test import APITestCase
from rest_framework import status
from djoser.utils import encode_uid
from django.contrib.auth.tokens import default_token_generator


User = get_user_model()


class UserRegistrationActivationTests(APITestCase):

    def setUp(self):
        # Djoser registration endpoint: POST /api/v1/auth/users/
        self.registration_url = reverse("user-list")
        # Custom activation endpoint: POST /accounts/activation/
        self.activation_url = reverse("accounts:email-activation")
        self.user_data = {
            "email": "testuser@example.com",
            "password": "Testpass123!",
            "re_password": "Testpass123!"
        }

    def test_user_registration_sends_activation_email(self):
        """Test registration creates user and sends activation email."""
        response = self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=self.user_data["email"])
        self.assertFalse(user.is_verified)
        # There should be one email in the outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Account activation", mail.outbox[0].subject)

    def test_activation_with_valid_token(self):
        """Test account activation with a valid token and uid."""
        self.client.post(self.registration_url, self.user_data, format="json")
        user = User.objects.get(email=self.user_data["email"])
        uid = encode_uid(user.pk)
        token = default_token_generator.make_token(user)
        response = self.client.post(
            self.activation_url,
            {"uid": uid, "token": token},
            format="json"
        )
        user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(user.is_verified)

    def test_activation_with_invalid_token(self):
        """Test activation with invalid token returns error."""
        self.client.post(self.registration_url, self.user_data, format="json")
        user = User.objects.get(email=self.user_data["email"])
        uid = encode_uid(user.pk)
        response = self.client.post(
            self.activation_url,
            {"uid": uid, "token": "invalidtoken"},
            format="json"
        )
        user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(user.is_verified)

    def test_cannot_login_before_activation(self):
        """Test that login is not allowed before account activation."""
        self.client.post(self.registration_url, self.user_data, format="json")
        response = self.client.post(reverse("jwt-create"), {
            "email": self.user_data["email"],
            "password": self.user_data["password"]
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unique_email_constraint(self):
        """Test that duplicate email registration is not allowed."""
        self.client.post(self.registration_url, self.user_data, format="json")
        response = self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_usermanager_create_staff(self):
        """Test that custom manager creates staff user with correct flags."""
        staff = User.objects.create_user(
            email="staff@example.com",
            password="12345",
            is_staff=True
        )
        self.assertTrue(staff.is_staff)
        self.assertFalse(staff.is_superuser)

    def test_usermanager_create_superuser(self):
        """Test that custom manager creates superuser with correct flags."""
        superuser = User.objects.create_superuser(
            email="super@example.com",
            password="12345"
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_registration_with_short_password(self):
        """Test registration fails with a short password."""
        data = {
            "email": "shortpass@example.com",
            "password": "123",
            "re_password": "123"
        }
        response = self.client.post(self.registration_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_registration_with_no_email(self):
        """Test registration fails if email is missing."""
        data = {
            "password": "ValidPass123!",
            "re_password": "ValidPass123!"
        }
        response = self.client.post(self.registration_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_with_non_matching_passwords(self):
        """Test registration fails if passwords do not match."""
        data = {
            "email": "mismatch@example.com",
            "password": "Password1$A",
            "re_password": "Password2$B"
        }
        response = self.client.post(self.registration_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_repeated_activation_link(self):
        """
        Test that activating an account twice:
        - First activation succeeds.
        - Second activation returns error (already activated or invalid token).
        """
        self.client.post(self.registration_url, self.user_data, format="json")
        user = User.objects.get(email=self.user_data["email"])
        uid = encode_uid(user.pk)
        token = default_token_generator.make_token(user)
        # First activation should succeed
        response1 = self.client.post(
            self.activation_url,
            {"uid": uid, "token": token},
            format="json"
        )
        user.refresh_from_db()
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertTrue(user.is_verified)
        # Second activation attempt with the same token should fail
        response2 = self.client.post(
            self.activation_url,
            {"uid": uid, "token": token},
            format="json"
        )
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
