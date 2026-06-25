# Tile Index Backend

FastAPI backend for the production multi-user Tile Index desktop application.

## Commands

Install:

```powershell
python -m pip install -r requirements.txt
```

Configure:

```powershell
copy .env.example .env
```

Migrate:

```powershell
alembic upgrade head
```

Seed defaults:

```powershell
python -m scripts.seed_defaults
```

Run:

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```
