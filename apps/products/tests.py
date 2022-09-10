from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User


class TestDownloadView(TestCase):
    def test_anonymous_cannot_see_page(self):
        response = self.client.get(reverse("test"))
        assert response.status_code == 302

    def test_authenticated_user_can_see_page(self):
        user = User.objects.create_user("Juliana," "juliana@dev.io", "some_pass")
        self.client.force_login(user=user)
        response = self.client.get(reverse("test"))
        assert response.status_code == 200
