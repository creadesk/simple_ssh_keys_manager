from cryptography.fernet import Fernet, InvalidToken
from .key_store import encryption_key_store


def get_fernet() -> Fernet:
    return Fernet(encryption_key_store.get_key())


def encrypt_private_key(plaintext: str) -> str:
    if not plaintext or not plaintext.strip():
        raise ValueError("Private Key darf nicht leer sein")
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_private_key(ciphertext: str) -> str:
    try:
        return get_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError(
            "Private Key konnte nicht entschlüsselt werden "
            "(falscher Encryption-Key oder korrupte Daten)."
        ) from e