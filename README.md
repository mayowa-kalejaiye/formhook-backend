# FormHook

A plug-and-play backend service for HTML forms. Accept submissions from static sites, store securely, and manage/export data with ease.
Frontend at https://github.com/mayowa-kalejaiye/formhook-frontend

## Features
- User authentication (JWT)
- Form creation and management
- Submission endpoint for static sites
- Submission storage and export (CSV)
- Email notifications (optional, per form)
- Advanced webhooks (custom headers, HMAC, retries, delivery logs)
- Rate limiting (5 submissions/minute per IP)
- Geolocation enrichment: submissions include country, region, city, latitude, longitude (if enabled per form)
- Device fingerprinting: store submitter IP, User-Agent, and inferred device type (mobile/tablet/desktop/bot)
- Submission analytics: breakdown by country, region, city, and time interval
- Abuse/threat monitoring: flags rapid submissions from same IP, datacenter IPs, and stores threat score

## Tech Stack
- FastAPI, SQLAlchemy, Alembic, PostgreSQL, python-dotenv
- Email: Resend API (or SendGrid)
- Geolocation: ipinfo.io (can be extended)

## Quickstart
1. Clone repo
2. Set up `.env` with your database and email API keys
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `alembic upgrade head`
5. Start dev server: `uvicorn formhook.app.main:app --reload`

---

## API Endpoints (MVP)

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

**Note:** A verification email will be sent to the provided email address.

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

**Note:** Email must be verified before login is allowed.

#### Verify Email
`POST /auth/verify-email`

**Payload:**
```json
{
  "token": "verification-token-from-email"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email verified successfully"
}
```

#### Request Email Verification
`POST /auth/request-verification`

**Payload:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "If your email exists in our system, you will receive a verification link"
}
```

#### Request Password Reset
`POST /auth/reset-password-request`

**Payload:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "If your email exists in our system, you will receive a password reset link"
}
```

#### Confirm Password Reset
`POST /auth/reset-password`

**Payload:**
```json
{
  "token": "reset-token-from-email",
  "password": "newpassword"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password updated successfully"
}
```

**Note:** Password resets invalidate previously issued JWT sessions.

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
  "webhook_headers": { "Authorization": "Bearer xyz" }, // optional, custom headers
  "webhook_secret": "supersecret", // optional, HMAC secret for signature
#### Webhook Delivery Logs
`GET /forms/{form_id}/webhook-deliveries`
**Headers:** `Authorization: Bearer <token>`
**Response:**
```json
[
  {
    "id": 1,
    "form_id": "form-uuid",
    "submission_id": 123,
    "webhook_url": "https://...",
    "status": "SUCCESS",
    "attempts": 1,
    "last_attempt_at": "2025-07-26T00:00:00.000000Z",
    "next_retry_at": null,
    "response_code": 200,
    "error_message": null,
    "success": true,
    "headers_sent": { "Authorization": "Bearer xyz" },
    "response_body": "...",
    "retry_count": 0,
    "duration_ms": 120
  }
]
```
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
  "country": "Nigeria",
  "region": "Lagos",
  "city": "Yaba",
  "location_source": "ipinfo.io",
  "latitude": "6.5244",
  "longitude": "3.3792",
  "threat_score": 0,
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
    "country": "Nigeria",
    "region": "Lagos",
    "city": "Yaba",
    "location_source": "ipinfo.io",
    "latitude": "6.5244",
    "longitude": "3.3792",
    "threat_score": 0,
    "created_at": "2025-07-25T12:34:56"
  }
]
```

#### Export Submissions (CSV)
`GET /forms/{form_id}/submissions/export`
**Headers:** `Authorization: Bearer <token>`
**Response:** CSV file download (includes geolocation fields)

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
- Auth endpoints use JWT Bearer tokens or API tokens.
- Submission endpoint is public, all others require authentication.
- Forms support custom field definitions via the `fields` array.
- Webhooks support custom headers, HMAC signatures, retries, and delivery logs.
- Submissions can be enriched with geolocation data if enabled per form.
- Analytics endpoints provide breakdowns by country, region, city, and time interval.
- Abuse/threat monitoring flags rapid submissions and datacenter IPs, storing a threat score per submission.
- See code for more details and TODOs.

## Trial Reminder Emails
- The API process launches a background task (enabled by default) that checks every `TRIAL_REMINDER_INTERVAL_MINUTES` (defaults to 60) and sends day-2/day-3 reminder emails automatically via Resend.
- Toggle the loop with `ENABLE_TRIAL_REMINDER_TASK=false` if you prefer external scheduling.
- A scheduler-friendly helper remains available at `python -m formhook.app.scripts.send_trial_reminders` if you need to trigger reminders from cron/CI.
- The command inspects `users.trial_ends_at`, skips admins, and records `trial_day2_email_sent_at` / `trial_day3_email_sent_at` in `subscription_metadata` to avoid duplicates.
