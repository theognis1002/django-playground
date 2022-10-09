from django.urls import path
from products.api.views import UserViewSet
from . import views
from rest_framework import routers


urlpatterns = [
    path("", views.index),
    path("atomic/", views.atomic_test, name="atomic"),
    path("test/", views.test_view, name="test"),
]

router = routers.SimpleRouter()
router.register(r"users", UserViewSet, basename="users")
urlpatterns += router.urls
