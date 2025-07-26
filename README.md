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

#### Signup
`POST /auth/signup`
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
  "name": "Newsletter Signup",
  "redirect_url": "https://mysite.com/thanks",
  "success_message": "Thanks for joining!",
  "description": "For website...", // optional
  "webhook_url": "https://...",   // optional
  "notification_email": "notify@...", // optional
  "fields": [
    { "name": "email", "label": "Email Address", "type": "email", "required": true },
    { "name": "name", "label": "Full Name", "type": "text", "required": false },
    { "name": "message", "label": "Message", "type": "textarea", "required": false }
  ]
}
```
**Field object:**
- `name`: string (e.g. "email")
- `label`: string (e.g. "Your Email")
- `type`: string, one of: "text", "email", "textarea", "checkbox", "select"
- `required`: boolean

**Response:**
```json
{
  "id": "form-uuid",
  "user_id": 1,
  "name": "Newsletter Signup",
  "redirect_url": "https://mysite.com/thanks",
  "success_message": "Thanks for joining!",
  "description": "For website...",
  "webhook_url": "https://...",
  "notification_email": "notify@...",
  "fields": [
    { "name": "email", "label": "Email Address", "type": "email", "required": true },
    { "name": "name", "label": "Full Name", "type": "text", "required": false },
    { "name": "message", "label": "Message", "type": "textarea", "required": false }
  ],
  "created_at": "2025-07-26T00:00:00.000000Z"
}
```


#### List Forms
`GET /forms/`
**Headers:** `Authorization: Bearer <token>`
**Response:**
```json
[
  {
    "id": "form-uuid",
    "user_id": 1,
    "name": "Newsletter Signup",
    "redirect_url": "https://mysite.com/thanks",
    "success_message": "Thanks for joining!",
    "description": "For website...",
    "webhook_url": "https://...",
    "notification_email": "notify@...",
    "fields": [
      { "name": "email", "label": "Email Address", "type": "email", "required": true },
      { "name": "name", "label": "Full Name", "type": "text", "required": false },
      { "name": "message", "label": "Message", "type": "textarea", "required": false }
    ],
    "created_at": "2025-07-26T00:00:00.000000Z"
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
- Forms now support custom field definitions via the `fields` array. See above for schema.
- See code for more details and TODOs.
