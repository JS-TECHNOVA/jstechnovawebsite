from django.core.management.base import BaseCommand

from website.views import bootstrap_homepage_defaults


class Command(BaseCommand):
    help = "Create the initial site content records in the database if they do not exist."

    def handle(self, *args, **options):
        bootstrap_homepage_defaults()
        self.stdout.write(self.style.SUCCESS("Initial site content is present in the database."))
