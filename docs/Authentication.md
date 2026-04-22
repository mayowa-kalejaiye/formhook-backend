# Authentication API

## POST `/auth/signup`

Register a new user.

### Request Body (JSON)
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

### Response (201 Created)
```json
{
  "email": "user@example.com",
  "id": 1,
  "created_at": "2025-07-26T00:00:00.000000Z"
}
```

---

## POST `/auth/login`

Authenticate a user and return a JWT access token.

### Request Body (JSON)
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

### Response (200 OK)
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

## POST `/auth/reset-password-request`

Request a password reset link.

### Request Body (JSON)
```json
{
  "email": "user@example.com"
}
```

### Response (200 OK)
```json
{
  "success": true,
  "message": "If your email exists in our system, you will receive a password reset link"
}
```

## POST `/auth/reset-password`

Reset a password using a token from the email link.

### Request Body (JSON)
```json
{
  "token": "reset-token-from-email",
  "password": "newpassword"
}
```

### Response (200 OK)
```json
{
  "success": true,
  "message": "Password updated successfully"
}
```

**Note:** Changing the password revokes previously issued JWT sessions.

---

## Notes
- Both endpoints expect and return JSON.
- On error, a JSON error message is returned with an appropriate HTTP status code.
- The JWT token can be used for authenticated requests to protected endpoints.
