# Yarosh-Portfolio
Photographer Oleksandra Yarosh's portfolio website

## Environment configuration

Copy `.env.example` to `.env` and set a private Django `SECRET_KEY`. The
development configuration keeps `DEBUG=True`; set the Telegram bot token and
chat ID to enable contact-form notifications. Leave either Telegram value
blank to keep requests in the database without sending notifications. Do not
commit `.env`.

Install project dependencies and apply migrations:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
```

## Database upgrades

The custom user model reuses Django's existing `auth_user` table and its user
relation tables. When upgrading a database that was already migrated with
Django's default user model, back up the database, then run:

```powershell
.\venv\Scripts\python.exe manage.py adopt_legacy_auth_user
.\venv\Scripts\python.exe manage.py migrate
```

For a new database, run `manage.py migrate` normally; do not run the adoption
command.
