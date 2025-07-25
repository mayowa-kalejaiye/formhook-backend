# FormHook

A plug-and-play backend service for HTML forms. Accept submissions from static sites, store securely, and manage/export data with ease.

## Features
- User authentication (JWT)
- Form creation and management
- Submission endpoint for static sites
- Submission storage and export (CSV)
- Optional: Email notifications, webhooks, rate limiting

## Tech Stack
- FastAPI, SQLAlchemy, Alembic, PostgreSQL, SendGrid, python-dotenv

## Quickstart
1. Clone repo
2. Set up `.env`
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `alembic upgrade head`
5. Start dev server: `uvicorn formhook.app.main:app --reload`

---

See code for detailed docs and TODOs.
