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

## API Endpoints

### Auth
#### Register
`POST /auth/register`
**Payload:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```
**Response:**
```json
{
  "id": 1,
  "email": "user@example.com"
}
```

#### Login
`POST /auth/login`
**Payload:**
```json
{
  "username": "user@example.com",
  "password": "yourpassword"
}
```
**Response:**
```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

### Forms
#### Create Form
`POST /forms/`
**Headers:** `Authorization: Bearer <token>`
**Payload:**
```json
{
  "name": "Contact Form",
  "notification_email": "notify@example.com",
  "webhook_url": "https://webhook.site/your-url"
}
```
**Response:**
```json
{
  "id": "form_id",
  "name": "Contact Form",
  "notification_email": "notify@example.com",
  "webhook_url": "https://webhook.site/your-url"
}
```

#### List Forms
`GET /forms/`
**Headers:** `Authorization: Bearer <token>`
**Response:**
```json
[
  {
    "id": "form_id",
    "name": "Contact Form",
    "notification_email": "notify@example.com",
    "webhook_url": "https://webhook.site/your-url"
  }
]
```

---

### Submissions
#### Submit to Form
`POST /forms/{form_id}/submit`
**Payload:**
```json
{
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello!"
  }
}
```
**Response:**
```json
{
  "id": 1,
  "form_id": "form_id",
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello!"
  },
  "ip_address": "127.0.0.1",
  "created_at": "2025-07-25T12:34:56"
}
```

#### List Submissions
`GET /forms/{form_id}/submissions?limit=20&offset=0`
**Headers:** `Authorization: Bearer <token>`
**Response:**
```json
[
  {
    "id": 1,
    "form_id": "form_id",
    "data": { ... },
    "ip_address": "127.0.0.1",
    "created_at": "2025-07-25T12:34:56"
  }
]
```

#### Export Submissions (CSV)
`GET /forms/{form_id}/submissions/export`
**Headers:** `Authorization: Bearer <token>`
**Response:** CSV file download

---

### Admin
#### Retry Pending Webhooks
`POST /forms/admin/retry-webhooks`
**Headers:** `Authorization: Bearer <token>`
**Response:**
```json
{
  "detail": "Webhook retry task started."
}
```

---

## Notes
- All endpoints return standard HTTP status codes and error messages.
- Auth endpoints use JWT Bearer tokens.
- Submission endpoint is public, all others require authentication.
- See code for more details and TODOs.
