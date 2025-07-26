
# FormHook API Documentation


## Authentication

### POST `/auth/signup`
**Description:** Register a new user.

**Request Body:**
```
{
  "email": "user@example.com",   // string, required, valid email
  "password": "yourpassword"      // string, required
}
```
**Response:**
```
{
  "id": 1,                        // integer, user ID
  "email": "user@example.com",   // string
  "created_at": "2025-07-26T00:00:00.000000Z" // ISO datetime
}
```
**Errors:**
- 400: Email already registered
- 422: Validation error

---


```
{
  "email": "user@example.com",   // string, required, valid email
  "password": "yourpassword"      // string, required
}
```
**Response:**
```
{
  "access_token": "<JWT_TOKEN>", // string
  "token_type": "bearer"         // string
}
```

**Errors:**
- 401: Invalid credentials
- 422: Validation error

---

## API Tokens (Authenticated, Bearer JWT or API token required)

### POST `/api-token/generate`
**Description:** Generate a new API token for the authenticated user. Only one active token per user. Rate limited (1/min per user).

**Headers:**
- Authorization: Bearer <token>

**Response:**
```json
{
  "api_token": "<API_TOKEN>" // string, only returned once
}
```
**Errors:**
- 401: Unauthorized
- 429: Rate limit exceeded (only one token generation per minute)

**Notes:**
- The API token is only shown once. Store it securely.
- Generating a new token revokes any previous token.
- The API token can be used as a Bearer token for all authenticated endpoints (in place of a JWT).

---

### DELETE `/api-token`
**Description:** Revoke the current API token for the authenticated user.

**Headers:**
- Authorization: Bearer <token>

**Response:**
```json
{
  "detail": "API token revoked."
}
```
**Errors:**
- 401: Unauthorized

---


## Dashboard

### GET `/dashboard/summary`
**Description:** Returns a summary for the authenticated user's dashboard, including:
- Total forms count
- Total submissions count
- Recent activity (last 5 submissions)
- Trend data (submissions per day for the selected range)
- Webhook stats (delivered, failed, pending)

**Headers:**
- Authorization: Bearer <token>

**Query Parameters:**
- `days`: int, optional (default 30) — Number of days for trend data

**Response:**
```json
{
  "total_forms": 3,
  "total_submissions": 42,
  "recent_submissions": [
    {
      "id": 123,
      "form_id": "form-uuid",
      "data": {"field1": "value1"},
      "ip_address": "127.0.0.1",
      "created_at": "2025-07-26T00:00:00.000000Z"
    }
    // ... up to 5 most recent submissions ...
  ],
  "trend": [
    {"date": "2025-07-01", "count": 2},
    {"date": "2025-07-02", "count": 0}
    // ... one entry per day for the selected range ...
  ],
  "webhook_stats": {
    "total": 10,
    "delivered": 8,
    "failed": 1,
    "pending": 1
  }
}
```
**Errors:**
- 401: Unauthorized

---

### GET `/forms/`

**Headers:**
- Authorization: Bearer <token>

**Response:**
```
[
    "id": "form-uuid",                // string (UUID)
    "user_id": 1,                       // integer
    "name": "Contact Form",            // string
    "description": "For website...",   // string or null
    "webhook_url": "https://...",      // string or null
    "notification_email": "notify@...",// string or null
    "created_at": "2025-07-26T00:00:00.000000Z" // ISO datetime
  },
```

**Description:** Create a new form for the authenticated user.
**Headers:**
- Authorization: Bearer <token>

**Request Body:**
```
  "name": "Contact Form",              // string, required
  "description": "For website...",     // string, optional
  "webhook_url": "https://...",        // string, optional, valid URL
  "notification_email": "notify@..."   // string, optional, valid email
}
```
**Response:**
```
  "id": "form-uuid",
  "name": "Contact Form",
  "description": "For website...",
- 400: Invalid notification_email
- 401: Unauthorized

---
### GET `/forms/{form_id}`
**Description:** Get a form by ID (must belong to current user).

**Headers:**
- Authorization: Bearer <token>

**Response:** Form object (see above)
**Errors:**
- 404: Form not found
- 401: Unauthorized


### DELETE `/forms/{form_id}`
  "detail": "Form deleted"
}
```
**Errors:**
- 404: Form not found
- 401: Unauthorized

---

## Submissions

### POST `/forms/{form_id}/submit`
**Description:** Public endpoint to submit form data. Rate limited (5/min per IP).

**Request Body:**
```
{
    "field1": "value1",               // any key-value pairs
  }
}
```
**Response:**
```
{
  "id": 1,                             // integer
  "form_id": "form-uuid",             // string (UUID)
  "data": { ... },                      // submitted data
  "ip_address": "127.0.0.1",          // string
  "created_at": "2025-07-26T00:00:00.000000Z"
}
```
**Errors:**
- 404: Form not found
- 429: Rate limit exceeded
- 422: Validation error

---

### GET `/forms/{form_id}/submissions`
**Description:** Get submissions for a form (auth required, must own form) with pagination and filtering.

**Headers:**
- Authorization: Bearer <token>

**Query Parameters:**
- `limit`: int, default 20, max results
- `offset`: int, default 0, skip N results
- `date_from`: string, ISO 8601, filter by created_at >=
- `date_to`: string, ISO 8601, filter by created_at <=
- `ip_address`: string, filter by IP

**Response:**
```
[
  {
    "id": 1,
    "form_id": "form-uuid",
    "data": { ... },
    "ip_address": "127.0.0.1",
    "created_at": "2025-07-26T00:00:00.000000Z"
  },
  ...
]
```
**Errors:**
- 404: Form not found or not authorized
- 401: Unauthorized

---

### GET `/forms/{form_id}/submissions/export`
**Description:** Export submissions as CSV (auth required, must own form).

**Headers:**
- Authorization: Bearer <token>

**Response:** CSV file download
**Errors:**
- 404: Form not found or no submissions
- 401: Unauthorized

---

### POST `/forms/admin/retry-webhooks`
**Description:** Manually retry all pending webhook deliveries (admin only).

**Headers:**
- Authorization: Bearer <token>

**Response:**
```
{
  "detail": "Webhook retry task started."
}
```
**Errors:**
- 401: Unauthorized

---

## Additional Notes
- All endpoints expect and return JSON unless otherwise noted.
- Authenticated endpoints require a Bearer JWT token in the `Authorization` header.
- On error, a JSON error message is returned with an appropriate HTTP status code.
- The JWT token can be used for authenticated requests to protected endpoints.
- `/forms/{form_id}/submit` is rate limited to 5 requests per minute per IP.
- If a form has a `notification_email`, an email is sent on each submission.
- If a form has a `webhook_url`, submissions are forwarded to that URL (with retry logic).
