from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status


class TestAuthTestView(TestCase):
    def test_anonymous_cannot_see_page(self):
        response = self.client.get(reverse("test"))
        assert response.status_code == status.HTTP_302_FOUND

    def test_authenticated_user_can_see_page(self):
        user = User.objects.create_user("Juliana," "juliana@dev.io", "some_pass")
        self.client.force_login(user=user)
        response = self.client.get(reverse("test"))
        assert response.status_code == status.HTTP_200_OK


class TestContactAPI(APITestCase):
    def test_get_request_users_view(self):
        response = self.client.get(reverse("users-list"))
        assert response.status_code == status.HTTP_200_OK

    def test_post_request_users_view(self):
        data = {
            "username": "Juliana1002",
            "email": "johndoe@gmail.com",
            "password": "FakePassword1234567890!",
        }
        response = self.client.post(reverse("users-list"), data=data)
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.count() == 1
        assert User.objects.first().username == data["username"]
