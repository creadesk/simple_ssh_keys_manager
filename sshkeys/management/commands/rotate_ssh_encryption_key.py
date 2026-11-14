# sshkeys/management/commands/rotate_ssh_encryption_key.py
import getpass
import os
import sys

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from cryptography.fernet import Fernet

from sshkeys.key_store import encryption_key_store
from sshkeys.models import SSHCredential
from sshkeys.crypto import decrypt_private_key, encrypt_private_key


class Command(BaseCommand):
    help = (
        "Rotiert den SSH Encryption Key: "
        "entschlüsselt alle Private Keys mit dem alten Key "
        "und verschlüsselt sie mit dem neuen Key."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--generate-new",
            action="store_true",
            help="Erzeugt einen neuen Fernet-Key und zeigt ihn an.",
        )

    def handle(self, *args, **options):
        if options["generate_new"]:
            new_key = Fernet.generate_key().decode("ascii")
            self.stdout.write(self.style.SUCCESS("Neuer Fernet-Key:"))
            self.stdout.write(new_key)
            self.stdout.write(
                self.style.WARNING(
                    "\nKey sicher notieren. Er wird NICHT gespeichert."
                )
            )
            return

        if not sys.stdin.isatty():
            raise CommandError("Interaktives Terminal erforderlich.")

        # --- Alten Key holen ---
        self.stdout.write("Zuerst den BISHERIGEN Encryption-Key eingeben.")
        old_key = getpass.getpass("Alter Key: ").strip()
        if not old_key:
            raise CommandError("Kein alter Key eingegeben.")

        try:
            encryption_key_store.set_key(old_key)
        except ValueError as e:
            raise CommandError(f"Alter Key ungültig: {e}")

        # Kurz testen, ob damit Daten lesbar sind
        credentials = list(SSHCredential.objects.all())
        if credentials:
            try:
                _ = credentials[0].get_private_key()
            except Exception as e:
                raise CommandError(
                    f"Mit dem alten Key können vorhandene Daten nicht "
                    f"entschlüsselt werden: {e}"
                )

        # --- Neuen Key holen ---
        self.stdout.write("")
        self.stdout.write("Jetzt den NEUEN Encryption-Key eingeben.")
        new_key = getpass.getpass("Neuer Key: ").strip()
        if not new_key:
            raise CommandError("Kein neuer Key eingegeben.")

        confirm = getpass.getpass("Neuen Key zur Bestätigung erneut eingeben: ").strip()
        if new_key != confirm:
            raise CommandError("Die beiden Eingaben stimmen nicht überein.")

        try:
            Fernet(new_key.encode("ascii") if isinstance(new_key, str) else new_key)
        except Exception as e:
            raise CommandError(f"Neuer Key ist kein gültiger Fernet-Key: {e}")

        if new_key == old_key:
            raise CommandError("Alter und neuer Key sind identisch – Abbruch.")

        # --- Umschlüsseln ---
        self.stdout.write("")
        self.stdout.write(f"Verschlüssele {len(credentials)} Credential(s) neu …")

        plaintext_keys = []
        for cred in credentials:
            try:
                pem = cred.get_private_key()  # noch mit altem Key
                plaintext_keys.append((cred, pem))
            except Exception as e:
                raise CommandError(
                    f"Fehler beim Entschlüsseln von '{cred.name}': {e}"
                )

        # Ab hier nur noch neuer Key
        encryption_key_store.set_key(new_key)


        try:
            with transaction.atomic():
                for cred, pem in plaintext_keys:
                    cred.set_private_key(pem)  # neu verschlüsseln
                    cred.save(update_fields=["encrypted_private_key", "updated_at"])
        except Exception as e:
            # Bei Fehler alten Key wiederherstellen, damit der Prozess nutzbar bleibt
            encryption_key_store.set_key(old_key)
            raise CommandError(f"Umschlüsselung fehlgeschlagen: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Fertig. {len(plaintext_keys)} Credential(s) wurden mit dem "
                f"neuen Key verschlüsselt.\n"
                f"Ab sofort nur noch den NEUEN Key verwenden."
            )
        )