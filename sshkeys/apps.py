# sshkeys/apps.py
import os
import sys
import getpass

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


# Management-Commands, die OHNE Encryption-Key laufen dürfen
SKIP_KEY_PROMPT_COMMANDS = {
    "makemigrations",
    "migrate",
    "showmigrations",
    "sqlmigrate",
    "check",
    "help",
    "version",
    "load_ssh_encryption_key",  # dieser Command regelt den Key selbst
    "collectstatic",
    "createsuperuser",
}


def _current_management_command() -> str | None:
    """Ermittelt den aktuell aufgerufenen manage.py-Command."""
    argv = sys.argv
    if len(argv) >= 2 and argv[0].endswith("manage.py"):
        return argv[1]
    # fallback: erstes nicht-options-argument
    for arg in argv[1:]:
        if not arg.startswith("-"):
            return arg
    return None


def _should_prompt_for_key() -> bool:
    """Entscheidet, ob beim Start nach dem Key gefragt werden soll."""
    # Bereits geladen (z. B. über Env in einem Parent-Prozess) → nichts tun
    from .key_store import encryption_key_store
    if encryption_key_store.is_loaded():
        return False

    # Env-Variable hat Vorrang (optional, für Automatisierung)
    if os.environ.get("SSH_KEY_ENCRYPTION_KEY"):
        return False

    cmd = _current_management_command()
    if cmd in SKIP_KEY_PROMPT_COMMANDS:
        return False

    # Django-Test-Runner / bestimmte interne Aufrufe schonen
    if "test" in sys.argv:
        return False

    return True


def _prompt_and_load_key() -> None:
    """Interaktive Eingabe – ohne gültigen Key wird der Prozess beendet."""
    from .key_store import encryption_key_store

    # Bei runserver nur im eigentlichen Child-Prozess fragen (nicht im Reloader)
    if os.environ.get("RUN_MAIN") == "true" or "runserver" not in sys.argv:
        pass  # normaler Fall
    elif "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
        # Parent-Prozess des Reloaders → hier nicht fragen
        return

    if not sys.stdin.isatty():
        raise ImproperlyConfigured(
            "SSH Encryption Key fehlt und es steht kein interaktives Terminal "
            "zur Verfügung. Bitte Key über die Umgebung setzen oder interaktiv starten."
        )

    print("", file=sys.stderr)
    print("=== SSH Encryption Key erforderlich ===", file=sys.stderr)
    print("Ohne diesen Key startet die Anwendung nicht.", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        key = getpass.getpass("SSH Encryption Key (Fernet) eingeben: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAbgebrochen.", file=sys.stderr)
        sys.exit(1)

    if not key:
        print("Kein Key eingegeben. Prozess wird beendet.", file=sys.stderr)
        sys.exit(1)

    try:
        encryption_key_store.set_key(key)
    except ValueError as e:
        print(f"Ungültiger Key: {e}", file=sys.stderr)
        sys.exit(1)

    print("SSH Encryption Key geladen. Starte Anwendung …\n", file=sys.stderr)


class SshkeysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sshkeys"

    def ready(self):
        # 1) Optional: Key aus Umgebung übernehmen (wird weiterhin nicht persistiert)
        env_key = os.environ.get("SSH_KEY_ENCRYPTION_KEY")
        if env_key:
            from .key_store import encryption_key_store
            if not encryption_key_store.is_loaded():
                try:
                    encryption_key_store.set_key(env_key)
                except ValueError as e:
                    raise ImproperlyConfigured(str(e)) from e
            return

        # 2) Interaktive Eingabe erzwingen
        if _should_prompt_for_key():
            _prompt_and_load_key()