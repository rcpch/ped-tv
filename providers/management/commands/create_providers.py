from django.core.management.base import BaseCommand

from providers.fixtures import PROVIDERS
from providers.models import Provider


class Command(BaseCommand):
    help = "Create default content providers (idempotent — skips existing entries)"

    def handle(self, *args, **options):
        created = 0
        for data in PROVIDERS:
            _, was_created = Provider.objects.get_or_create(
                name=data["name"],
                defaults={"url": data["url"]},
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {data['name']}")
            else:
                self.stdout.write(f"  Exists:  {data['name']}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {created} created, {len(PROVIDERS) - created} already existed."
            )
        )
