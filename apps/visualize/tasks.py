from django.apps import apps
from django.conf import settings

MigrationSnapshot = apps.get_model("visualize", "MigrationSnapshot")


def task_schedule_migration_snapshot(output_format=MigrationSnapshot.PDF):
    if getattr(settings, "MIGRATION_SNAPSHOT_MODEL", True):
        MigrationSnapshot.objects.create(output_format=output_format)
