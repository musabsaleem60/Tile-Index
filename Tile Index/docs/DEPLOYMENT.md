# Production Deployment Guide

## 1. Create PostgreSQL

Create a PostgreSQL database using Neon or another managed PostgreSQL provider. Save the connection string in `backend/.env`.

```env
DATABASE_URL=postgresql+psycopg://user:password@host/dbname?sslmode=require
SECRET_KEY=replace-with-a-long-random-secret
```

Never put `DATABASE_URL` inside the desktop app.

## 2. Run Backend Locally

```powershell
cd "E:\Projects\Tile Index\Tile Index\backend"
python -m pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m scripts.seed_defaults
uvicorn app.main:app --reload
```

Health check:

```text
http://localhost:8000/health
```

API docs:

```text
http://localhost:8000/docs
```

## 3. Migrate Existing SQLite Data

After the database schema exists:

```powershell
cd "E:\Projects\Tile Index\Tile Index\backend"
python -m scripts.sqlite_to_postgres "..\data\tile_index.db"
```

## 4. Desktop App Configuration

Set the API URL for the desktop app:

```powershell
$env:TILE_INDEX_API_URL="https://your-api-domain.com"
```

For packaged deployments, store the API URL in an installer-created environment variable or a small config file outside the executable.

## 5. Package Desktop App

```powershell
cd "E:\Projects\Tile Index\Tile Index"
python -m PyInstaller --noconsole --onedir --name "TileIndex" main.py
```

Send the whole folder:

```text
dist\TileIndex
```

## 6. Software Updates

Backend endpoint:

```text
GET /updates/latest
```

The desktop app should compare its local `APP_VERSION` with this endpoint and prompt the user when a newer version is available.

## 7. Backups

For Neon or managed PostgreSQL, enable provider backups where available. For self-hosted PostgreSQL, schedule:

```bash
pg_dump "$DATABASE_URL" > tile_index_backup.sql
```

Keep daily backups for at least 14 days and monthly backups for at least 6 months.
