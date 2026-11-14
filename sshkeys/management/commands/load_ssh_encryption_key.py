# sshkeys/management/commands/load_ssh_encryption_key.py
import getpass
import sys

from django.core.management.base import BaseCommand, CommandError
from cryptography.fernet import Fernet

from sshkeys.key_store import encryption_key_store


class Command(BaseCommand):
    help = (
        "Lädt den SSH Encryption Key (Fernet) interaktiv in den Prozessspeicher. "
        "Der Key wird nirgends persistiert."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--generate",
            action="store_true",
            help="Erzeugt einen neuen Fernet-Key und zeigt ihn an.",
        )
        parser.add_argument(
            "--stdin",
            action="store_true",
            help="Key von stdin lesen.",
        )

    def handle(self, *args, **options):
        if options["generate"]:
            key = Fernet.generate_key().decode("ascii")
            self.stdout.write(self.style.SUCCESS("Neuer Fernet-Key erzeugt:"))
            self.stdout.write(key)
            self.stdout.write(
                self.style.WARNING(
                    "\nDiesen Key sicher aufbewahren. Er wird NICHT gespeichert."
                )
            )
            return

        if options["stdin"]:
            key = sys.stdin.read().strip()
        else:
            key = getpass.getpass("SSH Encryption Key (Fernet) eingeben: ").strip()

        if not key:
            raise CommandError("Kein Key eingegeben.")

        try:
            encryption_key_store.set_key(key)
        except ValueError as e:
            raise CommandError(str(e))

        self.stdout.write(
            self.style.SUCCESS(
                "SSH Encryption Key erfolgreich in den Speicher geladen."
            )
        )