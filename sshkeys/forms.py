from django import forms
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet

from .models import SSHCredential


class SSHCredentialForm(forms.ModelForm):
    private_key = forms.CharField(
        label="SSH Private Key (PEM)",
        widget=forms.Textarea(attrs={
            "rows": 12,
            "placeholder": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
            "autocomplete": "off",
        }),
        required=False,
        strip=False,
        help_text="Bei Bearbeitung leer lassen, um den bestehenden Key zu behalten.",
    )

    class Meta:
        model = SSHCredential
        fields = ["name", "host", "port", "username", "public_key", "is_active"]
        widgets = {
            "public_key": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.pop("is_create", False)
        super().__init__(*args, **kwargs)
        # required NICHT auf True setzen – Prüfung erfolgt in clean()

    def clean(self):
        cleaned = super().clean()

        value = self.data.get("private_key", "")
        if isinstance(value, str):
            value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        else:
            value = ""

        if self.is_create and not value:
            self.add_error("private_key", "Private Key ist erforderlich.")
        elif value and "BEGIN" not in value:
            self.add_error("private_key", "Sieht nicht nach einem PEM-Private-Key aus.")
        else:
            cleaned["private_key"] = value
            if value:
                # Vor der Model-Validierung verschlüsselt auf die Instanz legen
                self.instance.set_private_key(value)

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        private_key = (self.cleaned_data.get("private_key") or "").strip()
        if private_key:
            instance.set_private_key(private_key)
        if commit:
            instance.save()
        return instance


class ConnectionTestForm(forms.Form):
    command = forms.CharField(
        label="Befehl",
        initial="uname -a",
        max_length=500,
        widget=forms.TextInput(attrs={"size": 60}),
    )


class RotateEncryptionKeyForm(forms.Form):
    old_key = forms.CharField(
        label="Bisheriger Encryption-Key",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )
    new_key = forms.CharField(
        label="Neuer Encryption-Key",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )
    new_key_confirm = forms.CharField(
        label="Neuen Key bestätigen",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )

    def clean_old_key(self):
        key = self.cleaned_data["old_key"].strip()
        try:
            Fernet(key.encode("ascii"))
        except Exception as e:
            raise ValidationError(f"Ungültiger Fernet-Key: {e}")
        return key

    def clean_new_key(self):
        key = self.cleaned_data["new_key"].strip()
        try:
            Fernet(key.encode("ascii"))
        except Exception as e:
            raise ValidationError(f"Ungültiger Fernet-Key: {e}")
        return key

    def clean(self):
        cleaned = super().clean()
        old_key = cleaned.get("old_key")
        new_key = cleaned.get("new_key")
        confirm = (cleaned.get("new_key_confirm") or "").strip()

        if new_key and confirm and new_key != confirm:
            self.add_error("new_key_confirm", "Die beiden neuen Keys stimmen nicht überein.")
        if old_key and new_key and old_key == new_key:
            self.add_error("new_key", "Alter und neuer Key sind identisch.")
        return cleaned