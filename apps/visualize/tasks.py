from django.apps import apps

MigrationSnapshot = apps.get_model("visualize", "MigrationSnapshot")


def task_schedule_migration_snapshot(output_format=MigrationSnapshot.PDF):
    MigrationSnapshot.objects.create(output_format=output_format)
