# Tile Index Production Architecture Plan

## Current State

The application is a Python Tkinter desktop app that directly reads and writes a local SQLite database through repository classes. This works for a single computer, but it is not safe for a live multi-user deployment because every installation would either have separate data or would need to share a SQLite file over a network.

## Main Limitations

- Desktop app has direct database access.
- SQLite is not suitable for concurrent writes from 3-5 active users.
- Passwords are hashed with plain SHA256 instead of a password-hashing algorithm designed for credentials.
- No API boundary, rate limiting, request validation, or token-based authentication.
- Invoice creation and stock deduction are not handled as one database transaction.
- No formal migration system for schema changes.
- No clean deployment boundary between client code and production data.
- No version/update service for installed desktop apps.
- No backup or restore workflow.

## Target Architecture

```text
TileIndex Desktop App
        |
        | HTTPS + JWT
        v
FastAPI Backend
        |
        | SQLAlchemy + Alembic
        v
PostgreSQL Database
```

The desktop app must never connect directly to PostgreSQL. It should call secure API endpoints. The backend owns authentication, permissions, validation, business rules, audit logs, invoice transactions, stock updates, reports, and app version metadata.

## Technology Choices

- Backend API: FastAPI
- Database: PostgreSQL
- ORM: SQLAlchemy 2.x
- Migrations: Alembic
- Validation: Pydantic
- Password hashing: bcrypt through Passlib
- Auth: JWT access tokens
- Deployment: Docker-compatible backend service
- Desktop packaging: PyInstaller
- Update metadata: backend `/updates/latest` endpoint

## Migration Strategy

1. Add backend alongside existing Tkinter app.
2. Define PostgreSQL schema using SQLAlchemy models and Alembic migrations.
3. Provide a SQLite-to-PostgreSQL migration script.
4. Add API endpoints for branches, users/auth, tiles, accessories, sanitary products, inventory, invoices, reports, and updates.
5. Switch the desktop app from direct repositories to an API client one module at a time.
6. Package the desktop app with API configuration only, never database credentials.
7. Deploy backend and database, then run acceptance testing with multiple users.

## Production Rules

- All stock-changing operations must be transactional.
- Employees can only access their assigned branch.
- Admins can manage catalog, users, reports, and all branches.
- Invoice numbers must be generated server-side under database lock/transaction protection.
- Every login, stock movement, invoice creation, product change, and user change should write an audit log.
- Backups must run outside the desktop app, against PostgreSQL.
- Desktop app version checks should happen at startup, with the backend controlling the latest version metadata.

## Rollout Recommendation

Use a free Neon PostgreSQL database for initial pilot use. Host the backend on a small cloud service or VPS. When the client depends on the app daily, move to a paid database/server plan with automated backups and monitoring.
