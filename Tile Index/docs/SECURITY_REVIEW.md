# Security Review

## Fixed In Target Architecture

- Production database credentials stay on the backend server only.
- Passwords use bcrypt hashing through Passlib.
- Desktop clients authenticate with JWT tokens.
- Employees are restricted to their assigned branch.
- Admin-only operations are enforced server-side.
- Stock and invoice mutations are centralized in backend transactions.

## Remaining Migration Work

- Switch all Tkinter windows from direct repositories to `desktop_client.ApiClient`.
- Add refresh-token support if sessions need to last multiple days.
- Add HTTPS-only deployment.
- Add rate limiting at reverse proxy or API gateway level.
- Add structured production logging and error tracking.
- Add automated backup verification.

## Operational Requirements

- Rotate `SECRET_KEY` if leaked.
- Never commit `.env`.
- Use separate development and production databases.
- Disable default admin password immediately after first production login.
