from django.contrib import admin
from . import models


@admin.register(models.MigrationSnapshot)
class MigrationSnapshot(admin.ModelAdmin):
    list_display = ["id", "output_format", "created_at", "modified_at"]
    list_filter = ["output_format"]
    readonly_fields = ("graph_source", "output_file", "created_at", "modified_at")
