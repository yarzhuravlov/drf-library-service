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
        self.registration_url = reverse("user-list")
        self.activation_url = reverse("user-activation")
        self.login_url = reverse("jwt-create")
        self.user_data = {
            "email": "testuser@example.com",
            "password": "Testpass123!",
            "re_password": "Testpass123!"
        }

    def test_user_registration_sends_activation_email(self):
        response = self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=self.user_data["email"])
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("activation", mail.outbox[0].subject.lower())

    def test_activation_with_valid_token(self):
        self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        user = User.objects.get(email=self.user_data["email"])
        uid = encode_uid(user.pk)
        token = default_token_generator.make_token(user)
        response = self.client.post(
            self.activation_url,
            {"uid": uid, "token": token},
            format="json"
        )
        user.refresh_from_db()
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        )
        self.assertTrue(user.is_active)

    def test_activation_with_invalid_token(self):
        self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        user = User.objects.get(email=self.user_data["email"])
        uid = encode_uid(user.pk)
        response = self.client.post(
            self.activation_url,
            {"uid": uid, "token": "invalidtoken"},
            format="json"
        )
        user.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertFalse(user.is_active)

    def test_cannot_login_before_activation(self):
        self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        response = self.client.post(
            self.login_url,
            {
                "email": self.user_data["email"],
                "password": self.user_data["password"]
            },
            format="json"
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_login_after_activation(self):
        self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        user = User.objects.get(email=self.user_data["email"])
        uid = encode_uid(user.pk)
        token = default_token_generator.make_token(user)
        self.client.post(
            self.activation_url,
            {"uid": uid, "token": token},
            format="json"
        )
        response = self.client.post(
            self.login_url,
            {
                "email": self.user_data["email"],
                "password": self.user_data["password"]
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_unique_email_constraint(self):
        self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        response = self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_with_short_password(self):
        data = {
            "email": "shortpass@example.com",
            "password": "123",
            "re_password": "123"
        }
        response = self.client.post(
            self.registration_url,
            data,
            format="json"
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("password", response.data)

    def test_registration_with_no_email(self):
        data = {
            "password": "ValidPass123!",
            "re_password": "ValidPass123!"
        }
        response = self.client.post(
            self.registration_url,
            data,
            format="json"
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("email", response.data)

    def test_registration_with_non_matching_passwords(self):
        data = {
            "email": "mismatch@example.com",
            "password": "Password1$A",
            "re_password": "Password2$B"
        }
        response = self.client.post(
            self.registration_url,
            data,
            format="json"
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("non_field_errors", response.data)

    def test_repeated_activation_link(self):
        self.client.post(
            self.registration_url,
            self.user_data,
            format="json"
        )
        user = User.objects.get(email=self.user_data["email"])
        uid = encode_uid(user.pk)
        token = default_token_generator.make_token(user)
        response1 = self.client.post(
            self.activation_url,
            {"uid": uid, "token": token},
            format="json"
        )
        user.refresh_from_db()
        self.assertIn(
            response1.status_code,
            [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        )
        self.assertTrue(user.is_active)
        response2 = self.client.post(
            self.activation_url,
            {"uid": uid, "token": token},
            format="json"
        )
        self.assertIn(
            response2.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]
        )
