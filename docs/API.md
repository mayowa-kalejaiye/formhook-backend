<!-- markdownlint-disable MD022 MD031 MD032 MD034 -->

# FormHook API Documentation

Base URL:
- <https://formhook-backend-rnvw.onrender.com>

## Authentication

### POST `/auth/signup`
Register a new user.

Request body:
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

Response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2025-07-26T00:00:00.000000Z"
}
```

Errors:
- 400: Email already registered
- 422: Validation error

### POST `/auth/login`
Authenticate a user and return a JWT bearer token.

Request body:
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

Response:
```json
{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_verified": true
  }
}
```

Errors:
- 401: Invalid credentials
- 422: Validation error

## Forms

All endpoints in this section require:
- Authorization: Bearer <JWT_TOKEN>

### GET `/forms/`
List forms owned by the authenticated user with metadata.

Response example:
```json
[
  {
    "id": "form-uuid",
    "user_id": 1,
    "name": "Contact Form",
    "description": "For website",
    "webhook_url": null,
    "notification_email": null,
    "created_at": "2025-07-26T00:00:00.000000Z",
    "submission_count": 12,
    "recent_submissions": 4,
    "last_submission_at": "2025-07-30T08:30:00.000000Z",
    "status": "active"
  }
]
```

### POST `/forms/`
Create a new form.

Request body:
```json
{
  "name": "Contact Form",
  "description": "For website",
  "webhook_url": "https://example.com/webhook",
  "notification_email": "notify@example.com",
  "redirect_url": "https://example.com/thanks",
  "success_message": "Thank you!",
  "fields": [
    {
      "name": "email",
      "label": "Email",
      "type": "email",
      "required": true
    }
  ]
}
```

Errors:
- 400: Invalid notification_email
- 401: Unauthorized

### GET `/forms/{form_id}`
Get a single form and metadata.

Errors:
- 404: Form not found
- 401: Unauthorized

### DELETE `/forms/{form_id}`
Delete a form.

Errors:
- 404: Form not found
- 401: Unauthorized

### POST `/forms/{form_id}/generate-token`
Generate a form-scoped API token.

Response:
```json
{
  "token": "<FORM_API_TOKEN>",
  "message": "Store this token securely. It will not be shown again."
}
```

### DELETE `/forms/{form_id}/revoke-token`
Revoke a form-scoped API token.

Response:
- 204 No Content

### GET `/forms/{form_id}/webhook-deliveries`
Get webhook delivery logs for a form.

### GET `/forms/public/{form_id}`
Public endpoint to fetch form metadata/fields for rendering.

## Submissions

### POST `/forms/{form_id}/submit`
Submit form data. Public endpoint.

Notes:
- If the form has `require_token = true`, include `Authorization: Bearer <FORM_API_TOKEN>`.
- If token is not required, submissions can be sent without Authorization.

Request body example:
```json
{
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello"
  }
}
```

### POST `/forms/public/{form_id}/submit`
Legacy public alias for submissions.

### GET `/forms/{form_id}/submissions`
Get submissions for a form (owner only).

Query parameters:
- `limit` (default 20)
- `offset` (default 0)
- `date_from` (ISO 8601)
- `date_to` (ISO 8601)
- `ip_address`

### GET `/forms/{form_id}/submissions/export`
Export submissions for a form as CSV (owner only).

### POST `/forms/admin/retry-webhooks`
Manually trigger retry of pending webhook deliveries.

## Dashboard and Analytics

All endpoints require bearer JWT authentication.

### GET `/dashboard/summary`
Returns dashboard summary for the current user.

### GET `/forms/{form_id}/analytics`
Returns analytics timeseries for a form.

Query parameters:
- `date_from` (ISO 8601)
- `date_to` (ISO 8601)
- `interval` (`day` or `hour`)

### GET `/forms/{form_id}/geo-analytics`
Returns analytics grouped by country/region/city.

## Notifications

All endpoints require bearer JWT authentication.

### GET `/notifications/`
List notifications.

### GET `/notifications/unread-count`
Get unread notifications count.

### POST `/notifications/{notification_id}/read`
Mark a notification as read.

### POST `/notifications/mark-all-read`
Mark all notifications as read.

### POST `/notifications/{notification_id}/archive`
Archive a notification.

### DELETE `/notifications/{notification_id}`
Delete a notification.

### GET `/notifications/preferences`
Get notification preferences.

### PUT `/notifications/preferences`
Update notification preferences.

## Push Notifications

All endpoints require bearer JWT authentication.

### POST `/notifications/push/subscribe`
Subscribe a device/browser push endpoint.

### POST `/notifications/push/unsubscribe`
Unsubscribe a push endpoint.

### GET `/notifications/push/vapid-key`
Get VAPID public key.

### GET `/notifications/push/subscriptions`
List push subscriptions.

### DELETE `/notifications/push/subscriptions/{subscription_id}`
Delete a push subscription.

### POST `/notifications/push/test`
Send a test push notification.
