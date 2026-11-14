Ein Prototyp, der SSH-Private-Keys verschlüsselt in der Datenbank speichert. 
Die Schlüssel selbst liegen dabei niemals als Datei auf dem Host-System. 
Zur Verschlüsselung kommt ein Fernet-Key zum Einsatz, der ausschließlich im Speicher des laufenden Prozesses gehalten wird und bei jedem Start manuell eingegeben werden muss.
Optional kann der Key als Umgebungsvariable gesetzt werden.

---

### Master-Key erzeugen
> Muss aus 32 kryptografisch zufälligen Bytes und URL-safer Codierung bestehen.

#### Alternative 1: mit Python
```bash
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

#### Alternative 2: mit OpenSSL
```bash
openssl rand -base64 32 | tr '+/' '-_' | tr -d '\\n'
```

Den angezeigten Key **sicher aufbewahren** (z. B. Password-Manager).  
Er wird von der Anwendung nicht gespeichert. Ohne diesen Key sind alle verschlüsselten SSH-Private-Keys unbrauchbar.

---

## Applikationsstart

```bash
python manage.py runserver
```
Beim Start von Befehlen wie `runserver` oder `shell` erscheint eine Eingabeaufforderung.

- Key eingeben → Anwendung startet  
- Leere Eingabe oder Abbruch → Prozess wird beendet  

Der Key gilt nur für diesen einen Prozess. Nach Neustart muss er erneut eingegeben werden.

**Optional:** Key über die Umgebung setzen (dann kein Prompt):

```bash
export SSH_KEY_ENCRYPTION_KEY="dein-fernet-key=="
python manage.py runserver
```

Bestimmte Verwaltungsbefehle (`migrate`, `makemigrations`, …) starten ohne Key-Abfrage.

---

## Test im Web-Browser
### Super-User anlegen
> python manage.py createsuperuser
### SSH-Keys verwalten
> http://127.0.0.1:8000


## Docker
```bash
mkdir -p ./zdockerdata/db

docker run -d \
  --name "simple_ssh_keys_manager" \
  -p 8000:8000 \
  -v "$(pwd)/zdockerdata/db:/app/db" \
  -e HOST_UID=$(id -u) \
  -e HOST_GID=$(id -g) \
  -e HOST_UNAME=$(id -un) \
  -e HOST_GNAME=$(id -gn) \
  -e DJANGO_SUPERUSER_USERNAME=admin \
  -e DJANGO_SUPERUSER_PASSWORD=admin \
  -e SECRET_KEY=<geheime_lange_zeichenkette> \
  -e SSH_KEY_ENCRYPTION_KEY=<fernet_key>> \
  -e DEBUG=true \
  -e ALLOWED_HOSTS=127.0.0.1,localhost \
  -e DB_ENGINE=django.db.backends.sqlite3 \
  -e DB_NAME=db/db.sqlite3 \
  simple_ssh_keys_manager:v0.0.0
```