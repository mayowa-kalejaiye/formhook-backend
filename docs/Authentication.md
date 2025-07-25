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
  "token_type": "bearer"
}
```

---

## Notes
- Both endpoints expect and return JSON.
- On error, a JSON error message is returned with an appropriate HTTP status code.
- The JWT token can be used for authenticated requests to protected endpoints.
