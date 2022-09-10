from django.urls import path

from . import views

urlpatterns = [
    path("", views.index),
    path("atomic/", views.atomic_test, name="atomic"),
    path("test/", views.test_view, name="test"),
]
