import io
import logging
from contextlib import contextmanager
from typing import Optional, Tuple

import paramiko
from paramiko import SSHClient, AutoAddPolicy, RSAKey, Ed25519Key, ECDSAKey
from paramiko.ssh_exception import SSHException, AuthenticationException

from .models import SSHCredential

logger = logging.getLogger(__name__)


def _load_pkey_from_string(private_key_pem: str, password: Optional[str] = None):
    key_file = io.StringIO(private_key_pem)
    for key_class in (Ed25519Key, ECDSAKey, RSAKey):
        try:
            key_file.seek(0)
            return key_class.from_private_key(key_file, password=password)
        except (SSHException, ValueError, paramiko.PasswordRequiredException):
            continue
    raise ValueError(
        "Private Key konnte nicht geladen werden. "
        "Unterstützte Formate: OpenSSH PEM (RSA, Ed25519, ECDSA)."
    )


@contextmanager
def ssh_connection(credential: SSHCredential, timeout: int = 15):
    if not credential.is_active:
        raise ValueError(f"Credential '{credential.name}' ist deaktiviert.")

    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())

    private_key_pem = None
    pkey = None

    try:
        private_key_pem = credential.get_private_key()
        pkey = _load_pkey_from_string(private_key_pem)

        client.connect(
            hostname=credential.host,
            port=credential.port,
            username=credential.username,
            pkey=pkey,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        yield client
    except AuthenticationException as e:
        logger.error("SSH Auth fehlgeschlagen für %s: %s", credential, e)
        raise
    except SSHException as e:
        logger.error("SSH Fehler für %s: %s", credential, e)
        raise
    finally:
        client.close()
        if private_key_pem is not None:
            del private_key_pem
        if pkey is not None:
            del pkey


def run_command(credential: SSHCredential, command: str, timeout: int = 30) -> Tuple[str, str, int]:
    with ssh_connection(credential) as client:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return out, err, exit_code