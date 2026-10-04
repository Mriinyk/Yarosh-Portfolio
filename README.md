# Yarosh-Portfolio
Photographer Oleksandra Yarosh's portfolio website

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
