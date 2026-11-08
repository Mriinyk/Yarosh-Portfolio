# Yarosh-Portfolio
Photographer Oleksandra Yarosh's portfolio website

## Environment configuration

Copy `.env.example` to `.env` and set a private Django `SECRET_KEY`. The
default settings module is `yarosh_web_portfolio.settings.development`, which
keeps `DEBUG=True` and uses SQLite. Set `DJANGO_SETTINGS_MODULE` to
`yarosh_web_portfolio.settings.production` in the deployment environment to use
PostgreSQL. The production environment also needs `ALLOWED_HOSTS` as a
comma-separated list of hostnames. Set the Telegram bot token and chat ID to
enable contact-form notifications; leave either value blank to disable them.
Do not commit `.env`.

Install project dependencies and apply local development migrations:

**Windows (PowerShell)**

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
```

**macOS and Linux**

```sh
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
python -m pip install -r requirements.txt
python manage.py migrate
```

Replace the example `SECRET_KEY` in `.env` with a private key before running
the application. To start the local development server, run
`python manage.py runserver` with the virtual environment activated.

## Production static files

Production uses WhiteNoise to serve compressed, fingerprinted static assets.
Before deployment, collect the assets using the production settings module:

```powershell
$env:DJANGO_SETTINGS_MODULE = "yarosh_web_portfolio.settings.production"
.\venv\Scripts\python.exe manage.py collectstatic --noinput
```

**macOS and Linux**

```sh
export DJANGO_SETTINGS_MODULE=yarosh_web_portfolio.settings.production
python manage.py collectstatic --noinput
```

The collected files are written to `staticfiles/`; WhiteNoise serves them from
there after the application starts.

## Database upgrades

The custom user model reuses Django's existing `auth_user` table and its user
relation tables. When upgrading a database that was already migrated with
Django's default user model, back up the database, then run:

```powershell
.\venv\Scripts\python.exe manage.py adopt_legacy_auth_user
.\venv\Scripts\python.exe manage.py migrate
```

**macOS and Linux**

```sh
python manage.py adopt_legacy_auth_user
python manage.py migrate
```

For a new database, run `manage.py migrate` normally; do not run the adoption
command.

## Restoring public site content

The portable public-content snapshot is stored in
`fixtures/site_content.json`. After cloning the repository and applying
migrations to a new database, restore it with:

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py restore_site_content
.\venv\Scripts\python.exe manage.py createsuperuser
```

**macOS and Linux**

```sh
python manage.py migrate
python manage.py restore_site_content
python manage.py createsuperuser
```

The restore command imports hero slides, photo-session types and sessions, and
the biography. It refuses to run if hero slides or photo sessions already
exist, so it will not overwrite content in a populated database. User accounts,
contact-form submissions, likes, comments, shares, and visitor statistics are
intentionally excluded from the portable fixture. Uploaded media files are
stored separately from the database and must be transferred separately if
used.

## Photo sessions and site statistics

Manage photo-session types and sessions in Django admin. The public
`/photos/` page supports title/type search, database-backed type filters,
pagination (nine sessions per page), galleries, likes, comments, and share
tracking. Superusers can also add, edit, and delete sessions from that page.
Create custom types in the “Photo session types” admin section or from the
session editor's “Add a new type” option.

The footer shows the number of photo sessions and unique browser profiles.
Unique visitors are counted once using a signed, first-party, one-year cookie;
the counter is refreshed in the browser every 15 seconds. Clearing cookies or
using another browser profile will be counted as a new visitor. No IP address
or browser fingerprint is stored for this counter.
