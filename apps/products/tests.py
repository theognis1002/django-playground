import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

pytestmark = pytest.mark.django_db


class TestAuthTestView(TestCase):
    def test_anonymous_cannot_see_page(self):
        response = self.client.get(reverse("test"))
        assert response.status_code == status.HTTP_302_FOUND

    def test_authenticated_user_can_see_page(self):
        user = User.objects.create_user("Juliana," "juliana@dev.io", "some_pass")
        self.client.force_login(user=user)
        response = self.client.get(reverse("test"))
        assert response.status_code == status.HTTP_200_OK


class TestUsersAPI(APITestCase):
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


def test_does_not_make_unnecessary_queries(client, django_assert_max_num_queries):
    with django_assert_max_num_queries(2):
        client.get(reverse("users-list"))


class TestPerfViews:
    def test_does_not_make_unnecessary_queries(
        self, client, django_assert_max_num_queries
    ):
        with django_assert_max_num_queries(2):
            client.get(reverse("users-list"))
