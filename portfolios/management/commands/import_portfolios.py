import json
from django.core.management.base import BaseCommand, CommandError
from portfolios.services import import_workbook


class Command(BaseCommand):
    help = "Importa el Excel original de forma validada, atómica y repetible."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        try:
            result = import_workbook(path=options["path"])
        except (ValueError, OSError, KeyError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result))
