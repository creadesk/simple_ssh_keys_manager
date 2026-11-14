import os
import threading
from typing import Optional
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured


class EncryptionKeyStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._key: Optional[bytes] = None

    def set_key(self, key: str | bytes) -> None:
        if isinstance(key, str):
            key = key.strip().encode("ascii")
        try:
            Fernet(key)
        except Exception as e:
            raise ValueError(
                "Ungültiger Fernet-Key. Bitte einen mit "
                "`Fernet.generate_key()` erzeugten Key verwenden."
            ) from e
        with self._lock:
            self._key = key
            os.environ["SSH_KEY_ENCRYPTION_KEY"] = key.decode("ascii")

    def get_key(self) -> bytes:
        with self._lock:
            if self._key is None:
                raise ImproperlyConfigured(
                    "SSH Encryption Key wurde noch nicht geladen. "
                    "Bitte zuerst `python manage.py load_ssh_encryption_key` ausführen."
                )
            return self._key

    def is_loaded(self) -> bool:
        with self._lock:
            return self._key is not None

    def clear(self) -> None:
        with self._lock:
            self._key = None


encryption_key_store = EncryptionKeyStore()