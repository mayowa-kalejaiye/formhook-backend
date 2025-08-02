
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



## Dashboard & Analytics

### GET `/dashboard/summary`
Returns a summary for the authenticated user's dashboard, including:
- Total forms count
- Total submissions count
- Recent activity (last 5 submissions)
- Trend data (submissions per day for the selected range)
- Webhook stats (delivered, failed, pending)

### GET `/forms/{form_id}/analytics`
Returns analytics for a form, grouped by day (or hour), for the past 30 days by default. Includes:
- Submissions per interval
- Failed webhooks per interval
- Emails sent per interval
- Unique IPs per interval

### GET `/forms/{form_id}/geo-analytics`
Returns breakdown of submissions by country, region, and city, with date filtering. Example response:
```json
{
  "country_stats": [
    {"name": "Nigeria", "count": 12},
    {"name": "United States", "count": 5}
  ],
  "region_stats": [
    {"name": "Lagos", "count": 10},
    {"name": "California", "count": 3}
  ],
  "city_stats": [
    {"name": "Yaba", "count": 7},
    {"name": "San Francisco", "count": 2}
  ]
}
```

All analytics endpoints require authentication and only return data for forms owned by the authenticated user.

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



### GET `/forms/{form_id}/analytics`

**Description:** Returns analytics for a form, grouped by day (or hour), for the past 30 days by default. Protected with JWT. Only returns data for forms owned by the authenticated user.

**Headers:**

- Authorization: Bearer <token>

**Query Parameters:**

- `date_from`: ISO 8601 datetime, optional (default: 30 days ago)
- `date_to`: ISO 8601 datetime, optional (default: now)
- `interval`: "day" (default) or "hour"

**Response:**

```json
[
  {
    "date": "2025-07-20",
    "submissions": 50,
    "failed_webhooks": 3,
    "emails_sent": 40,
    "unique_ips": 10
  },
  ...
]
```

**Field meanings:**

- `submissions`: Number of submissions for the form on that day/hour
- `failed_webhooks`: Number of webhook events with status = "failed" for that form and day/hour
- `emails_sent`: Number of successful notification emails sent for that form and day/hour (tracked in EmailLog)
- `unique_ips`: Number of unique IP addresses that submitted to the form on that day/hour

**Errors:**

- 403: Not authorized to access this form
- 401: Unauthorized

---

### Email Logging

Notification emails sent for form submissions are logged in the `EmailLog` table. Each log entry includes:
- `form_id`: The form the email was sent for
- `submission_id`: The submission that triggered the email (if any)
- `to_email`: Recipient email address
- `status`: "SENT" or "FAILED"
- `created_at`: Timestamp of the email event

This enables accurate analytics for the `emails_sent` metric in the analytics endpoint.

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

```json
{
  "detail": "Webhook retry task started."
}
```

**Errors:**

- 401: Unauthorized

---


## Additional Notes
- All endpoints expect and return JSON unless otherwise noted.
- Authenticated endpoints require a Bearer JWT token or API token in the `Authorization` header.
- On error, a JSON error message is returned with an appropriate HTTP status code.
- The JWT token or API token can be used for authenticated requests to protected endpoints.
- `/forms/{form_id}/submit` is rate limited to 5 requests per minute per IP.
- If a form has a `notification_email`, an email is sent on each submission.
- If a form has a `webhook_url`, submissions are forwarded to that URL (with retry logic).
- Submissions can be enriched with geolocation data (country, region, city, latitude, longitude) if enabled per form.
- Analytics endpoints provide breakdowns by country, region, city, and time interval.
- Abuse/threat monitoring flags rapid submissions and datacenter IPs, storing a threat score per submission.
