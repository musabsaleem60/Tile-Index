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

## 2A. Deploy Backend To Render

Push the repository to GitHub, then create a Render Web Service.

Recommended Render settings:

```text
Repository: Tile-Index
Branch: main
Root Directory: Tile Index/backend
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: bash start.sh
```

Required Render environment variables:

```env
APP_NAME=Tile Index API
APP_ENV=production
APP_VERSION=1.0.0
SECRET_KEY=<long-random-secret>
ACCESS_TOKEN_EXPIRE_MINUTES=480
DATABASE_URL=postgresql+psycopg://...
BACKEND_CORS_ORIGINS=
LATEST_DESKTOP_VERSION=1.0.0
LATEST_DESKTOP_DOWNLOAD_URL=
LATEST_DESKTOP_RELEASE_NOTES=Initial production backend
```

After deploy, test:

```text
https://your-render-service-url.onrender.com/health
https://your-render-service-url.onrender.com/docs
```

## 3. Migrate Existing SQLite Data

After the database schema exists:

```powershell
cd "E:\Projects\Tile Index\Tile Index\backend"
python -m scripts.sqlite_to_postgres "..\data\tile_index.db"
```

## 4. Desktop App Configuration

For development, set the API URL with an environment variable:

```powershell
$env:TILE_INDEX_API_URL="https://your-api-domain.com"
```

For packaged deployments, create `tile_index_config.json` beside the executable:

```json
{
  "api_base_url": "https://your-render-service-url.onrender.com",
  "check_updates": true
}
```

## 5. Package Desktop App

```powershell
cd "E:\Projects\Tile Index\Tile Index"
.\scripts\build_desktop.ps1 -ApiBaseUrl "https://your-render-service-url.onrender.com"
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

To publish an app update:

1. Update code.
2. Increment `APP_VERSION` in `desktop_client/config.py`.
3. Build desktop package again.
4. Upload installer/package to a download URL.
5. Set Render environment variables:

```env
LATEST_DESKTOP_VERSION=1.0.1
LATEST_DESKTOP_DOWNLOAD_URL=https://your-download-url/TileIndex-1.0.1.zip
LATEST_DESKTOP_RELEASE_NOTES=Describe what changed
```

6. Restart/redeploy backend.
7. Client apps will show an update notification at startup.

## 7. Backups

For Neon or managed PostgreSQL, enable provider backups where available. For self-hosted PostgreSQL, schedule:

```bash
pg_dump "$DATABASE_URL" > tile_index_backup.sql
```

Keep daily backups for at least 14 days and monthly backups for at least 6 months.
