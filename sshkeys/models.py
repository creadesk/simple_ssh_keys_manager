from django.db import models
from .crypto import encrypt_private_key, decrypt_private_key


class SSHCredential(models.Model):
    name = models.CharField(max_length=100, unique=True)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=22)
    username = models.CharField(max_length=100)
    encrypted_private_key = models.TextField(
        help_text="Private Key (PEM), verschlüsselt gespeichert"
    )
    public_key = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "SSH Credential"
        verbose_name_plural = "SSH Credentials"

    def __str__(self):
        return f"{self.name} ({self.username}@{self.host})"

    def set_private_key(self, private_key_pem: str) -> None:
        self.encrypted_private_key = encrypt_private_key(private_key_pem)

    def get_private_key(self) -> str:
        return decrypt_private_key(self.encrypted_private_key)

    def clean(self):
        # Validierung des Klartext-Keys übernimmt das Formular.
        # encrypted_private_key wird erst beim save() gesetzt.
        pass