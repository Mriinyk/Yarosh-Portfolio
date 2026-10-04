from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, transaction

from yarosh_website.models import (
    Biography,
    HeroSlide,
    PhotoSession,
    PhotoSessionType,
)


DEFAULT_PHOTO_TYPES = [
    ("Портрети", 1),
    ("Тематичні фотосесії", 2),
    ("Заходи", 3),
    ("Корпоративні фотосесії", 4),
]


class Command(BaseCommand):
    help = "Restore public site content from fixtures/site_content.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=connections,
            help="Database to restore the site content into.",
        )

    def handle(self, *args, **options):
        del args
        database = options["database"]
        fixture = Path(settings.BASE_DIR) / "fixtures" / "site_content.json"
        if not fixture.is_file():
            raise CommandError(f"Site-content fixture not found: {fixture}")

        with transaction.atomic(using=database):
            if HeroSlide.objects.using(database).exists() or PhotoSession.objects.using(
                database
            ).exists():
                raise CommandError(
                    "Site content already exists. Restore only into a new database."
                )

            existing_types = list(
                PhotoSessionType.objects.using(database)
                .order_by("order", "name")
                .values_list("name", "order")
            )
            if existing_types != DEFAULT_PHOTO_TYPES:
                raise CommandError(
                    "Photo-session types differ from the migrated defaults. "
                    "Restore only into a new database."
                )
            if Biography.objects.using(database).count() > 1:
                raise CommandError(
                    "Multiple biography records exist. Restore only into a new database."
                )

            Biography.objects.using(database).all().delete()
            PhotoSessionType.objects.using(database).all().delete()
            call_command(
                "loaddata",
                str(fixture),
                database=database,
                verbosity=options["verbosity"],
            )

        self.stdout.write(self.style.SUCCESS("Site content restored successfully."))
