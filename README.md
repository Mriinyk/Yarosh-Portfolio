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

## Restoring public site content

The portable public-content snapshot is stored in
`fixtures/site_content.json`. After cloning the repository and applying
migrations to a new database, restore it with:

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py restore_site_content
.\venv\Scripts\python.exe manage.py createsuperuser
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
