from django.urls import path

from . import views

urlpatterns = [
    path("", views.index),
    path("atomic/", views.atomic_test),
]
