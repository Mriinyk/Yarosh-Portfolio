from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.db import connections
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = (
        "Mark the initial custom-user migration applied when adopting the "
        "existing Django auth_user tables without changing their data."
    )
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")

    def handle(self, **options):
        connection = connections[options["database"]]
        User = apps.get_model("yarosh_website", "User")
        groups_through = User._meta.get_field("groups").remote_field.through
        permissions_through = (
            User._meta.get_field("user_permissions").remote_field.through
        )
        expected_tables = {
            User._meta.db_table: {
                field.column for field in User._meta.local_fields
            },
            groups_through._meta.db_table: {
                "id",
                "user_id",
                "group_id",
            },
            permissions_through._meta.db_table: {
                "id",
                "user_id",
                "permission_id",
            },
        }

        recorder = MigrationRecorder(connection)
        if recorder.migration_qs.filter(
            app="yarosh_website",
            name="0001_initial",
        ).exists():
            self.stdout.write("The initial Yarosh user migration is already recorded.")
            return

        existing_tables = set(connection.introspection.table_names())
        if not set(expected_tables).issubset(existing_tables):
            missing = ", ".join(sorted(set(expected_tables) - existing_tables))
            raise CommandError(
                "The legacy auth tables are incomplete; no migration history "
                f"was changed. Missing: {missing}. Run migrate normally on a "
                "new database."
            )

        with connection.cursor() as cursor:
            for table, required_columns in expected_tables.items():
                columns = {
                    column.name
                    for column in connection.introspection.get_table_description(
                        cursor,
                        table,
                    )
                }
                missing_columns = required_columns - columns
                if missing_columns:
                    raise CommandError(
                        f"Table {table} does not match the legacy Django user "
                        f"schema; missing columns: {', '.join(sorted(missing_columns))}."
                    )

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        try:
            migration = loader.get_migration("yarosh_website", "0001_initial")
        except KeyError as error:
            raise CommandError(
                "The initial Yarosh user migration has not been generated."
            ) from error

        if not migration.initial:
            raise CommandError(
                "yarosh_website.0001_initial is not marked as an initial migration."
            )

        applied = recorder.applied_migrations()
        unapplied_dependencies = [
            dependency
            for dependency in migration.dependencies
            if dependency[0] != "__setting__" and dependency not in applied
        ]
        if unapplied_dependencies:
            missing = ", ".join(
                f"{app}.{name}" for app, name in unapplied_dependencies
            )
            raise CommandError(
                "The legacy auth migration dependencies are not applied: "
                f"{missing}. No migration history was changed."
            )

        recorder.record_applied("yarosh_website", "0001_initial")
        self.stdout.write(
            self.style.SUCCESS(
                "Verified the existing auth_user tables and preserved all user "
                "records. The initial Yarosh user migration is now recorded; "
                "run manage.py migrate next."
            )
        )
