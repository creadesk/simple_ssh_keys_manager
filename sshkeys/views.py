from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from sshkeys.forms import ConnectionTestForm, RotateEncryptionKeyForm, SSHCredentialForm
from sshkeys.key_store import encryption_key_store
from sshkeys.models import SSHCredential
from sshkeys.ssh_service import run_command


def superuser_required(view):
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser
    )(view)

@superuser_required
def credential_list(request):
    credentials = SSHCredential.objects.order_by("name")
    return render(request, "sshkeys/credential_list.html", {
        "credentials": credentials,
        "key_loaded": encryption_key_store.is_loaded(),
    })


@superuser_required
@require_http_methods(["GET", "POST"])
def credential_create(request):
    if request.method == "POST":
        form = SSHCredentialForm(request.POST, is_create=True)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "SSH-Credential gespeichert.")
                return redirect("list")
            except Exception as e:
                messages.error(request, f"Speichern fehlgeschlagen: {e}")
        else:
            # Debug – nach dem Fix wieder entfernen
            print("Form-Fehler:", form.errors)
    else:
        form = SSHCredentialForm(is_create=True)

    return render(request, "sshkeys/credential_form.html", {
        "form": form,
        "title": "SSH-Key hinterlegen",
    })

@superuser_required
@require_http_methods(["GET", "POST"])
def credential_edit(request, pk):
    cred = get_object_or_404(SSHCredential, pk=pk)
    form = SSHCredentialForm(request.POST or None, instance=cred, is_create=False)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, "SSH-Credential aktualisiert.")
            return redirect("list")
        except Exception as e:
            messages.error(request, f"Aktualisieren fehlgeschlagen: {e}")
    return render(request, "sshkeys/credential_form.html", {
        "form": form,
        "title": f"Bearbeiten: {cred.name}",
        "credential": cred,
    })


@superuser_required
@require_http_methods(["POST"])
def credential_delete(request, pk):
    cred = get_object_or_404(SSHCredential, pk=pk)
    name = cred.name
    cred.delete()
    messages.success(request, f"„{name}“ gelöscht.")
    return redirect("list")


@superuser_required
@require_http_methods(["GET", "POST"])
def connection_test(request, pk):
    cred = get_object_or_404(SSHCredential, pk=pk)
    form = ConnectionTestForm(request.POST or None)
    result = None

    if request.method == "POST" and form.is_valid():
        command = form.cleaned_data["command"]
        try:
            stdout, stderr, code = run_command(cred, command)
            result = {
                "ok": True,
                "stdout": stdout,
                "stderr": stderr,
                "code": code,
                "command": command,
            }
        except Exception as e:
            result = {
                "ok": False,
                "error": str(e),
                "command": command,
            }

    return render(request, "sshkeys/connection_test.html", {
        "credential": cred,
        "form": form,
        "result": result,
    })


@superuser_required
@require_http_methods(["GET", "POST"])
def rotate_encryption_key(request):
    form = RotateEncryptionKeyForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        old_key = form.cleaned_data["old_key"]
        new_key = form.cleaned_data["new_key"]

        try:
            # Mit altem Key laden und alle PEMs lesen
            encryption_key_store.set_key(old_key)
            credentials = list(SSHCredential.objects.all())
            plaintext_keys = []
            for cred in credentials:
                plaintext_keys.append((cred, cred.get_private_key()))

            # Auf neuen Key umstellen und neu verschlüsseln
            encryption_key_store.set_key(new_key)
            with transaction.atomic():
                for cred, pem in plaintext_keys:
                    cred.set_private_key(pem)
                    cred.save(update_fields=["encrypted_private_key", "updated_at"])

            messages.success(
                request,
                f"Rotation erfolgreich. {len(plaintext_keys)} Credential(s) "
                "wurden umgeschlüsselt. Ab sofort nur noch den neuen Key verwenden.",
            )
            return redirect("list")
        except Exception as e:
            # Versuch, den zuvor im Prozess geladenen Zustand nicht schlimmer zu machen:
            # wenn möglich alten Key wieder setzen
            try:
                encryption_key_store.set_key(old_key)
            except Exception:
                pass
            messages.error(request, f"Rotation fehlgeschlagen: {e}")

    return render(request, "sshkeys/rotate_key.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect('list')