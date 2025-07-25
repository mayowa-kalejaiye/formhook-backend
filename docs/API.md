
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

### POST `/auth/login`
**Description:** Authenticate a user and return a JWT access token.

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
  "access_token": "<JWT_TOKEN>", // string
  "token_type": "bearer"         // string
}
```
**Errors:**
- 401: Invalid credentials
- 422: Validation error

---

## Forms (Authenticated, Bearer JWT required)

### GET `/forms/`
**Description:** Get all forms for the current user.

**Headers:**
- Authorization: Bearer <token>

**Response:**
```
[
  {
    "id": "form-uuid",                // string (UUID)
    "user_id": 1,                       // integer
    "name": "Contact Form",            // string
    "description": "For website...",   // string or null
    "webhook_url": "https://...",      // string or null
    "notification_email": "notify@...",// string or null
    "created_at": "2025-07-26T00:00:00.000000Z" // ISO datetime
  },
  ...
]
```

---

### POST `/forms/`
**Description:** Create a new form for the authenticated user.

**Headers:**
- Authorization: Bearer <token>

**Request Body:**
```
{
  "name": "Contact Form",              // string, required
  "description": "For website...",     // string, optional
  "webhook_url": "https://...",        // string, optional, valid URL
  "notification_email": "notify@..."   // string, optional, valid email
}
```
**Response:**
```
{
  "id": "form-uuid",
  "user_id": 1,
  "name": "Contact Form",
  "description": "For website...",
  "webhook_url": "https://...",
  "notification_email": "notify@...",
  "created_at": "2025-07-26T00:00:00.000000Z"
}
```
**Errors:**
- 400: Invalid notification_email
- 401: Unauthorized
- 422: Validation error

---

### GET `/forms/{form_id}`
**Description:** Get a form by ID (must belong to current user).

**Headers:**
- Authorization: Bearer <token>

**Response:** Form object (see above)
**Errors:**
- 404: Form not found
- 401: Unauthorized

---

### DELETE `/forms/{form_id}`
**Description:** Delete a form by ID (must belong to current user).

**Headers:**
- Authorization: Bearer <token>

**Response:**
```
{
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
  "data": {
    "field1": "value1",               // any key-value pairs
    "field2": "value2"
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
