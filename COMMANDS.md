# AWAS — Developer Command Reference

This document provides quick commands for running, maintaining, and developing the **AWAS** system with PostgreSQL.

> **Working Directory**: `c:\Users\daryl\CascadeProjects\Awas\`  
> Always activate your virtual environment before executing commands:  
> `venv\Scripts\activate`

---

## 1. Virtual Environment

```powershell
# Activate virtual environment (PowerShell)
venv\Scripts\activate

# Deactivate
deactivate
```

---

## 2. Dependencies

```powershell
# Install all required packages (including psycopg2-binary for PostgreSQL)
pip install -r requirements.txt

# Install / update PostgreSQL driver only
pip install psycopg2-binary==2.9.9
```

---

## 3. Database Migrations (PostgreSQL)

```powershell
# Run all pending migrations
python manage.py migrate

# Create new migrations after changing any models.py
python manage.py makemigrations

# Check status of all migrations
python manage.py showmigrations

# Validate system & database connection
python manage.py check --database default
```

---

## 4. Admin Account (Create Superuser)

```powershell
# Create an admin account to access the dashboard and admin panel
python manage.py createsuperuser
```
Follow the interactive prompts:
- **Username**: e.g., `admin`
- **Email**: e.g., `admin@awas.local`
- **Password**: (type password and confirm)

Log in to the Admin Panel at: [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## 5. Starting and Stopping the Application

### 1-Click Batch Scripts:
- **`start.bat`**: Activates `venv`, checks migrations, and starts the server in the current single terminal window (`http://127.0.0.1:8000/`).
- **`stop.bat`**: Automatically finds and terminates any AWAS server processes listening on port 8000.

### Manual Commands:
```powershell
# Start local development server (http://127.0.0.1:8000/)
python manage.py runserver

# Start on a custom port
python manage.py runserver 8080

# Start accessible across local network (for testing on mobile/tablet)
python manage.py runserver 0.0.0.0:8000
```

---

## 6. Switching Between PostgreSQL and SQLite

In your [`.env`](file:///c:/Users/daryl/CascadeProjects/Awas/.env) file:

```env
# To use PostgreSQL (default):
DB_ENGINE=postgresql
DB_NAME=awas_db
DB_USER=postgres
DB_PASSWORD=root
DB_HOST=localhost
DB_PORT=5432

# To switch back to SQLite at any time:
DB_ENGINE=sqlite3
```

---

## 7. Data Backup & Restore

```powershell
# Backup entire PostgreSQL database to a JSON fixture
python manage.py dumpdata --natural-foreign --natural-primary --exclude=contenttypes --exclude=auth.permission --indent=2 -o backup_data.json

# Restore / load data from a JSON fixture
python manage.py loaddata backup_data.json
```

---

## 8. Django Interactive Shell

```powershell
# Launch interactive Django shell
python manage.py shell

# Quick test database connection in shell:
# >>> from django.db import connection
# >>> connection.ensure_connection()
# >>> print(connection.vendor)  # prints: postgresql
```

---

## 9. Static Files (Production Asset Collection)

```powershell
# Collect static files into staticfiles/
python manage.py collectstatic --noinput
```

---

## 10. Celery & Redis (Background Tasks)

```powershell
# Start Celery worker (requires Redis server running)
celery -A awas_project worker --loglevel=info

# Start Celery Beat scheduler
celery -A awas_project beat --loglevel=info
```
