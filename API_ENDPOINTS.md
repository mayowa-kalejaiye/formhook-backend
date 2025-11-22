# FormHook API Endpoints Documentation

Complete API reference for all FormHook backend endpoints with request/response payloads.

**Base URL:** `http://localhost:8000` (development) / `https://api.formhook.com` (production)

**Version:** 1.0.0  

---

### 8. Logout

**POST** `/auth/logout`

Clear the HttpOnly `access_token` cookie to log the user out.

**Request**
- No body required. If using cookies, make the request with credentials included.

**Example (fetch)**
```js
await fetch('https://formhook-backend.onrender.com/auth/logout', {
  method: 'POST',
  credentials: 'include',
});
```

**Example (axios)**
```js
await axios.post('https://formhook-backend.onrender.com/auth/logout', {}, { withCredentials: true });
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Logged out"
}
```

**Notes:**
- The endpoint deletes the `access_token` cookie on the client. After calling this endpoint, the frontend should also clear any in-memory user state.
- If your frontend relies on cookies for authentication, ensure `credentials: 'include'` or `withCredentials: true` is set and that CORS `allow_credentials` is enabled on the backend.

---

### 7. OAuth2 Token (Standard OAuth Flow)
## 📑 Table of Contents

1. [Authentication Endpoints](#authentication-endpoints)
2. [Form Management Endpoints](#form-management-endpoints)
3. [Submission Endpoints](#submission-endpoints)
4. [Subscription & Pricing Endpoints](#subscription--pricing-endpoints)
5. [Analytics Endpoints](#analytics-endpoints)
6. [Dashboard Endpoints](#dashboard-endpoints)
7. [Root Endpoints](#root-endpoints)

---

## 🔐 Authentication Endpoints

All authenticated endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### 1. User Registration

**POST** `/auth/signup`

Create a new user account and send verification email.

**Request Body** (JSON or Form Data):
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2025-10-23T12:00:00Z",
  "is_verified": false
}
```

**Error Responses:**
- `400` - User already exists or invalid email format
- `422` - Missing required fields

---

### 2. User Login

**POST** `/auth/login`

Authenticate user and receive JWT access token.

**Request Body** (JSON):
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_verified": true
  }
}
```

**Error Responses:**
- `401` - Invalid credentials
- `422` - Missing required fields

---

### 3. Email-Based Login (Passwordless)

**POST** `/auth/email-login`

Request a passwordless login link via email.

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200 OK):
```json
{
  "message": "Login link sent to your email",
  "email": "user@example.com"
}
```

---

### 4. Email Verification

**POST** `/auth/verify-email`

Verify user email with token from verification email.

**Request Body**:
```json
{
  "token": "verification-token-from-email"
}
```

**Response** (200 OK):
```json
{
  "message": "Email verified successfully",
  "verified": true
}
```

**Error Responses:**
- `400` - Invalid or expired token
- `404` - Verification record not found

---

### 5. Request Email Verification

**POST** `/auth/request-verification`

Resend email verification link.

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200 OK):
```json
{
  "message": "Verification email sent",
  "email": "user@example.com"
}
```

---

### 6. Check User Exists

**GET** `/auth/check-user/{email}`

Check if a user account exists for the given email.

**Path Parameters:**
- `email` - Email address to check

**Response** (200 OK):
```json
{
  "exists": true,
  "email": "user@example.com"
}
```

---

### 7. OAuth2 Token (Standard OAuth Flow)

**POST** `/auth/token`

OAuth2-compatible token endpoint for standard authentication flows.

**Request Body** (Form Data):
```
username=user@example.com
password=SecurePassword123!
grant_type=password
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 📝 Form Management Endpoints

### 1. List All Forms (with Metadata)

**GET** `/forms/`  
🔒 **Requires Authentication**

Get all forms for the authenticated user with submission statistics.

**Response** (200 OK):
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": 1,
    "name": "Contact Form",
    "description": "Main website contact form",
    "webhook_url": "https://example.com/webhook",
    "webhook_headers": {"X-Custom": "header"},
    "webhook_secret": null,
    "notification_email": "notify@example.com",
    "redirect_url": "https://example.com/thank-you",
    "success_message": "Thank you for contacting us!",
    "fields": [
      {
        "name": "email",
        "label": "Email Address",
        "type": "email",
        "required": true
      },
      {
        "name": "message",
        "label": "Message",
        "type": "textarea",
        "required": true
      }
    ],
    "created_at": "2025-10-01T10:00:00Z",
    "require_token": false,
    "submission_count": 45,
    "recent_submissions": 12,
    "last_submission_at": "2025-10-23T08:30:00Z",
    "status": "active"
  }
]
```

---

### 2. Create New Form

**POST** `/forms/`  
🔒 **Requires Authentication**

Create a new form for the authenticated user.

**Request Body**:
```json
{
  "name": "Contact Form",
  "description": "Main website contact form",
  "webhook_url": "https://example.com/webhook",
  "webhook_headers": {"X-Custom": "header"},
  "notification_email": "notify@example.com",
  "redirect_url": "https://example.com/thank-you",
  "success_message": "Thank you!",
  "fields": [
    {
      "name": "email",
      "label": "Email Address",
      "type": "email",
      "required": true
    },
    {
      "name": "name",
      "label": "Full Name",
      "type": "text",
      "required": true
    },
    {
      "name": "message",
      "label": "Message",
      "type": "textarea",
      "required": false
    }
  ]
}
```

**Field Types:** `text`, `email`, `textarea`, `checkbox`, `select`

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": 1,
  "name": "Contact Form",
  "description": "Main website contact form",
  "fields": [...],
  "created_at": "2025-10-23T12:00:00Z",
  "require_token": false
}
```

**Error Responses:**
- `402` - Form limit exceeded for current pricing tier
- `400` - Invalid field definitions

---

### 3. Get Form Details (with Metadata)

**GET** `/forms/{form_id}`  
🔒 **Requires Authentication**

Get detailed information about a specific form including submission statistics.

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": 1,
  "name": "Contact Form",
  "description": "Main website contact form",
  "webhook_url": "https://example.com/webhook",
  "fields": [...],
  "submission_count": 45,
  "recent_submissions": 12,
  "last_submission_at": "2025-10-23T08:30:00Z",
  "status": "active"
}
```

**Error Responses:**
- `404` - Form not found or not authorized

---

### 4. Get Public Form Structure

**GET** `/forms/public/{form_id}`  
🌐 **Public Endpoint** (No Authentication Required)

Get form structure for rendering public forms. Returns only public information.

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Contact Form",
  "description": "Main website contact form",
  "fields": [
    {
      "name": "email",
      "label": "Email Address",
      "type": "email",
      "required": true
    },
    {
      "name": "message",
      "label": "Message",
      "type": "textarea",
      "required": true
    }
  ]
}
```

**Note:** Does not include sensitive information like webhook URLs, API tokens, or user IDs.

---

### 5. Delete Form

**DELETE** `/forms/{form_id}`  
🔒 **Requires Authentication**

Delete a form (must be the owner).

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (200 OK):
```json
{
  "message": "Form deleted successfully"
}
```

**Error Responses:**
- `404` - Form not found or not authorized

---

### 6. Generate API Token for Form

**POST** `/forms/{form_id}/generate-token`  
🔒 **Requires Authentication**

Generate a unique API token for form submissions. Token is returned once and stored hashed.

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (200 OK):
```json
{
  "api_token": "fh_1234567890abcdef",
  "message": "API token generated successfully. Save this token - it won't be shown again.",
  "form_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Note:** Token should be saved immediately as it cannot be retrieved again.

---

### 7. Revoke API Token

**DELETE** `/forms/{form_id}/revoke-token`  
🔒 **Requires Authentication**

Revoke the API token for a form.

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (204 No Content)

---

### 8. Get Webhook Delivery Logs

**GET** `/forms/{form_id}/webhook-deliveries`  
🔒 **Requires Authentication**

Get webhook delivery logs for a form.

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "form_id": "123e4567-e89b-12d3-a456-426614174000",
    "submission_id": 456,
    "status": "delivered",
    "attempts": 1,
    "last_attempt_at": "2025-10-23T10:00:00Z",
    "response_code": 200,
    "error_message": null
  }
]
```

---

## 📨 Submission Endpoints

### 1. Submit Form Data

**POST** `/forms/{form_id}/submit`  
🌐 **Public Endpoint** (Rate Limited: 5 submissions/minute per IP)

Submit data to a form. If `require_token` is enabled, requires API token in Authorization header.

**Path Parameters:**
- `form_id` - UUID of the form

**Headers** (if token required):
```
Authorization: Bearer <form-api-token>
```

**Request Body**:
```json
{
  "data": {
    "email": "user@example.com",
    "name": "John Doe",
    "message": "Hello, I'd like to get in touch!"
  }
}
```

**Response** (200 OK):
```json
{
  "id": 456,
  "form_id": "123e4567-e89b-12d3-a456-426614174000",
  "data": {
    "email": "user@example.com",
    "name": "John Doe",
    "message": "Hello, I'd like to get in touch!"
  },
  "created_at": "2025-10-23T12:00:00Z",
  "ip_address": "192.168.1.1",
  "country": "United States",
  "city": "New York"
}
```

**Error Responses:**
- `401` - Invalid or missing API token (if required)
- `404` - Form not found
- `429` - Rate limit exceeded
- `503` - Form submission limit reached (owner needs to upgrade)

---

### 2. Get Form Submissions

**GET** `/forms/{form_id}/submissions`  
🔒 **Requires Authentication**

Get all submissions for a form (must be owner).

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (200 OK):
```json
[
  {
    "id": 456,
    "form_id": "123e4567-e89b-12d3-a456-426614174000",
    "data": {
      "email": "user@example.com",
      "message": "Hello!"
    },
    "created_at": "2025-10-23T12:00:00Z",
    "ip_address": "192.168.1.1",
    "country": "United States"
  }
]
```

---

### 3. Export Submissions (CSV)

**GET** `/forms/{form_id}/submissions/export`  
🔒 **Requires Authentication**

Export all form submissions as CSV file.

**Path Parameters:**
- `form_id` - UUID of the form

**Response** (200 OK):
```
Content-Type: text/csv
Content-Disposition: attachment; filename=submissions_{form_id}.csv

id,email,message,created_at,ip_address,country
456,user@example.com,Hello!,2025-10-23T12:00:00Z,192.168.1.1,United States
```

---

### 4. Retry Failed Webhooks (Admin)

**POST** `/forms/admin/retry-webhooks`  
🔒 **Requires Authentication**

Retry all failed webhook deliveries.

**Response** (200 OK):
```json
{
  "message": "Webhook retry initiated",
  "retried_count": 5
}
```

---

## 💳 Subscription & Pricing Endpoints

### 1. Get Pricing Plans

**GET** `/subscription/plans`  
🌐 **Public Endpoint**

Get all available pricing plans and features.

**Response** (200 OK):
```json
{
  "plans": {
    "free": {
      "name": "Developer Starter",
      "price_monthly": 0,
      "price_yearly": 0,
      "monthly_submissions": 100,
      "max_forms": 3,
      "max_team_members": 1,
      "file_upload_size_mb": 1,
      "features": [
        "basic_analytics",
        "email_notifications",
        "api_access",
        "community_support"
      ],
      "support_level": "community",
      "sla_uptime": null,
      "remove_branding": false,
      "white_label": false
    },
    "starter": {
      "name": "Starter",
      "price_monthly": 900,
      "price_yearly": 9000,
      "monthly_submissions": 1000,
      "max_forms": null,
      "max_team_members": 1,
      "file_upload_size_mb": 5,
      "features": [
        "basic_analytics",
        "email_notifications",
        "api_access",
        "email_support",
        "basic_integrations",
        "remove_branding"
      ],
      "support_level": "email",
      "sla_uptime": 0.99,
      "remove_branding": true,
      "white_label": false
    },
    "professional": {
      "name": "Professional",
      "price_monthly": 2900,
      "price_yearly": 29000,
      "monthly_submissions": 10000,
      "max_forms": null,
      "features": [
        "advanced_analytics",
        "webhooks",
        "ab_testing",
        "priority_email_support"
      ]
    },
    "business": {
      "name": "Business",
      "price_monthly": 9900,
      "price_yearly": 99000,
      "monthly_submissions": 100000,
      "features": [
        "white_label",
        "phone_support",
        "custom_fields",
        "priority_processing"
      ]
    },
    "enterprise": {
      "name": "Enterprise",
      "price_monthly": 19900,
      "price_yearly": 199000,
      "monthly_submissions": 1000000,
      "features": [
        "sso_integration",
        "dedicated_support",
        "custom_integrations",
        "dedicated_infrastructure"
      ]
    }
  },
  "currency": "USD",
  "updated_at": "2025-10-23T12:00:00Z"
}
```

**Note:** Prices are in cents (900 = $9.00)

---

### 2. Get Current Subscription

**GET** `/subscription/current`  
🔒 **Requires Authentication**

Get current user's subscription information and usage.

**Response** (200 OK):
```json
{
  "user_id": 1,
  "tier": "professional",
  "plan_name": "Professional",
  "status": "active",
  "billing_cycle": "monthly",
  "price_monthly": 2900,
  "price_yearly": 29000,
  "subscription_start_date": "2025-10-01T00:00:00Z",
  "subscription_end_date": null,
  "current_period_start": "2025-10-01T00:00:00Z",
  "next_billing_date": "2025-11-01T00:00:00Z",
  "stripe_customer_id": "cus_123456",
  "stripe_subscription_id": "sub_123456",
  "usage_info": {
    "submissions_used": 3450,
    "submissions_limit": 10000,
    "submissions_remaining": 6550,
    "usage_percentage": 34.5,
    "is_over_limit": false,
    "forms_count": 12,
    "overage_cost_cents": 0,
    "days_remaining": 8
  },
  "features": [
    "advanced_analytics",
    "webhooks",
    "ab_testing"
  ],
  "upgrade_available": true
}
```

---

### 3. Get Usage Statistics

**GET** `/subscription/usage`  
🔒 **Requires Authentication**

Get detailed usage statistics for current billing period.

**Response** (200 OK):
```json
{
  "user_id": 1,
  "current_tier": "professional",
  "billing_cycle": "monthly",
  "current_period_start": "2025-10-01T00:00:00Z",
  "next_reset_date": "2025-11-01T00:00:00Z",
  "days_remaining": 8,
  "submissions_used": 3450,
  "submissions_limit": 10000,
  "submissions_remaining": 6550,
  "usage_percentage": 34.5,
  "is_over_limit": false,
  "forms_count": 12,
  "forms_limit": null,
  "overage_cost_cents": 0,
  "overage_cost_formatted": "Free",
  "plan_name": "Professional",
  "plan_price": "$29",
  "upgrade_available": true
}
```

---

### 4. Get Usage Analytics

**GET** `/subscription/analytics?days=30`  
🔒 **Requires Authentication**

Get historical usage analytics with daily breakdown.

**Query Parameters:**
- `days` - Number of days to analyze (1-365, default: 30)

**Response** (200 OK):
```json
{
  "user_id": 1,
  "period_days": 30,
  "start_date": "2025-09-23T12:00:00Z",
  "end_date": "2025-10-23T12:00:00Z",
  "total_submissions": 3450,
  "average_daily": 115.0,
  "peak_day": {
    "date": "2025-10-15",
    "submissions": 287
  },
  "daily_breakdown": {
    "2025-10-23": 123,
    "2025-10-22": 98,
    "2025-10-21": 145
  },
  "current_tier": "professional",
  "usage_efficiency": 34.5
}
```

---

### 5. Get Tier Recommendation

**GET** `/subscription/recommendation`  
🔒 **Requires Authentication**

Get AI-powered tier recommendation based on usage patterns.

**Response** (200 OK) - If recommendation available:
```json
{
  "user_id": 1,
  "current_tier": "professional",
  "type": "upgrade",
  "recommended_tier": "business",
  "reason": "You're using 87.3% of your current plan",
  "plan_name": "Business",
  "monthly_cost": "$70",
  "additional_submissions": 90000
}
```

**Response** (200 OK) - If no recommendation:
```json
null
```

---

### 6. Upgrade Subscription

**POST** `/subscription/upgrade`  
🔒 **Requires Authentication**

Initiate subscription upgrade to a higher tier.

**Request Body**:
```json
{
  "target_tier": "business",
  "billing_cycle": "monthly"
}
```

**Response** (200 OK):
```json
{
  "message": "Upgrade initiated",
  "current_tier": "professional",
  "target_tier": "business",
  "target_plan": "Business",
  "price_change": 7000,
  "billing_cycle": "monthly",
  "effective_immediately": true,
  "next_steps": [
    "Payment processing will be handled by Stripe",
    "Subscription will be upgraded immediately upon successful payment",
    "New limits will take effect immediately"
  ]
}
```

**Error Responses:**
- `400` - Invalid tier or upgrade path

---

### 7. Downgrade Subscription

**POST** `/subscription/downgrade`  
🔒 **Requires Authentication**

Initiate subscription downgrade to a lower tier.

**Request Body**:
```json
{
  "target_tier": "starter",
  "billing_cycle": "monthly"
}
```

**Response** (200 OK):
```json
{
  "message": "Downgrade initiated",
  "current_tier": "professional",
  "target_tier": "starter",
  "target_plan": "Starter",
  "savings": 2000,
  "billing_cycle": "monthly",
  "effective_date": "End of current billing period",
  "next_steps": [
    "Downgrade will take effect at the end of your current billing period",
    "You'll retain current features until the effective date",
    "Billing will be adjusted automatically"
  ]
}
```

**Error Responses:**
- `400` - Invalid tier or not a downgrade
- `409` - Current usage exceeds target tier limits

---

### 8. Cancel Subscription

**POST** `/subscription/cancel`  
🔒 **Requires Authentication**

Cancel current paid subscription (downgrades to free at period end).

**Response** (200 OK):
```json
{
  "message": "Subscription cancelled",
  "current_tier": "professional",
  "status": "cancelled",
  "active_until": "2025-11-01T00:00:00Z",
  "downgrade_to": "free",
  "next_steps": [
    "Your subscription will remain active until the end of the current billing period",
    "You'll be downgraded to the free tier after expiration",
    "All data will be preserved"
  ]
}
```

---

### 9. Reactivate Subscription

**POST** `/subscription/reactivate`  
🔒 **Requires Authentication**

Reactivate a cancelled subscription before it expires.

**Response** (200 OK):
```json
{
  "message": "Subscription reactivated",
  "tier": "professional",
  "status": "active",
  "billing_cycle": "monthly"
}
```

---

### 10. Get Billing History

**GET** `/subscription/billing-history`  
🔒 **Requires Authentication**

Get billing history and invoices (requires Stripe integration).

**Response** (200 OK):
```json
{
  "message": "Billing history endpoint",
  "user_id": 1,
  "stripe_customer_id": "cus_123456",
  "note": "This endpoint will be implemented with Stripe integration",
  "billing_history": []
}
```

---

### 11. Validate Feature Access

**POST** `/subscription/validate-feature?feature=webhooks`  
🔒 **Requires Authentication**

Check if user has access to a specific feature.

**Query Parameters:**
- `feature` - Feature name to validate

**Response** (200 OK):
```json
{
  "has_access": true,
  "feature": "webhooks",
  "tier": "professional"
}
```

**Response** (200 OK) - No access:
```json
{
  "has_access": false,
  "feature": "white_label",
  "tier": "professional",
  "error": {
    "error": "Feature not available",
    "message": "The 'white_label' feature is not available on your current plan (Professional)",
    "current_tier": "professional",
    "feature": "white_label",
    "upgrade_required": {
      "required_tier": "business",
      "required_name": "Business",
      "required_price": "$99"
    }
  }
}
```

---

## 📊 Analytics Endpoints

### 1. Get Geo Analytics

**GET** `/forms/{form_id}/geo-analytics?date_from=2025-10-01&date_to=2025-10-23`  
🔒 **Requires Authentication**

Get geographic breakdown of form submissions.

**Path Parameters:**
- `form_id` - UUID of the form

**Query Parameters:**
- `date_from` - Start date (ISO 8601 format, optional)
- `date_to` - End date (ISO 8601 format, optional)

**Response** (200 OK):
```json
{
  "country_stats": [
    {"name": "United States", "count": 234},
    {"name": "United Kingdom", "count": 89},
    {"name": "Canada", "count": 45}
  ],
  "region_stats": [
    {"name": "California", "count": 87},
    {"name": "New York", "count": 65},
    {"name": "Texas", "count": 54}
  ],
  "city_stats": [
    {"name": "New York", "count": 45},
    {"name": "Los Angeles", "count": 38},
    {"name": "Chicago", "count": 27}
  ]
}
```

---

### 2. Get Form Analytics

**GET** `/forms/{form_id}/analytics?date_from=2025-10-01&date_to=2025-10-23&interval=day`  
🔒 **Requires Authentication**

Get detailed form analytics with time-series data.

**Path Parameters:**
- `form_id` - UUID of the form

**Query Parameters:**
- `date_from` - Start date (optional, default: 30 days ago)
- `date_to` - End date (optional, default: now)
- `interval` - Time interval: `day` or `hour` (default: `day`)

**Response** (200 OK):
```json
[
  {
    "date": "2025-10-23",
    "submissions": 123,
    "failed_webhooks": 2,
    "emails_sent": 120,
    "unique_ips": 98
  },
  {
    "date": "2025-10-22",
    "submissions": 145,
    "failed_webhooks": 0,
    "emails_sent": 145,
    "unique_ips": 112
  }
]
```

---

## 📊 Dashboard Endpoints

### 1. Get Dashboard Summary

**GET** `/dashboard/summary?days=30`  
🔒 **Requires Authentication**

Get comprehensive dashboard summary for the current user.

**Query Parameters:**
- `days` - Number of days for trend data (default: 30)

**Response** (200 OK):
```json
{
  "total_forms": 12,
  "total_submissions": 3450,
  "recent_submissions": [
    {
      "id": 456,
      "form_id": "123e4567-e89b-12d3-a456-426614174000",
      "data": {"email": "user@example.com"},
      "created_at": "2025-10-23T12:00:00Z"
    }
  ],
  "trend": [
    {"date": "2025-10-23", "count": 123},
    {"date": "2025-10-22", "count": 145},
    {"date": "2025-10-21", "count": 98}
  ],
  "webhook_stats": {
    "total": 3450,
    "delivered": 3380,
    "failed": 45,
    "pending": 25
  }
}
```

---

## 🏠 Root Endpoints

### 1. Root

**GET** `/`  
🌐 **Public Endpoint**

API root endpoint.

**Response** (200 OK):
```json
{
  "message": "Welcome to FormHook!"
}
```

---

### 2. Health Check

**GET** `/health`  
🌐 **Public Endpoint**

Health check endpoint for deployment monitoring.

**Response** (200 OK):
```json
{
  "status": "ok"
}
```

---

### 3. Email Verification Redirect

**GET** `/verify-email?token={verification_token}`  
🌐 **Public Endpoint**

Redirects email verification links to the frontend verification page.

**Query Parameters:**
- `token` - Email verification token

**Response** (302 Redirect):
Redirects to: `{FRONTEND_URL}/verify-email?token={token}`

---

## 📝 Common Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created successfully |
| `204` | No Content | Request successful, no response body |
| `400` | Bad Request | Invalid request format or parameters |
| `401` | Unauthorized | Missing or invalid authentication |
| `402` | Payment Required | Upgrade required for this operation |
| `403` | Forbidden | Not authorized to access this resource |
| `404` | Not Found | Resource not found |
| `409` | Conflict | Request conflicts with current state |
| `422` | Unprocessable Entity | Validation error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Service temporarily unavailable |

---

## 🔑 Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Obtaining a Token:**
1. Register via `/auth/signup`
2. Login via `/auth/login` to receive JWT token
3. Use token for authenticated requests

**Token Expiration:**
- Tokens expire after 24 hours
- Request a new token via `/auth/login`

---

## 🚀 Rate Limiting

**Public Submission Endpoint:**
- `/forms/{form_id}/submit` - 5 requests per minute per IP address

**Other Endpoints:**
- No rate limiting currently (subject to fair use)

---

## 🎯 Pricing Tiers Summary

| Tier | Price | Submissions/Month | Forms | Key Features |
|------|-------|-------------------|-------|--------------|
| **Free** | $0 | 100 | 3 | Basic analytics, community support |
| **Starter** | $9 | 1,000 | Unlimited | Remove branding, email support |
| **Professional** | $29 | 10,000 | Unlimited | Webhooks, A/B testing, advanced analytics |
| **Business** | $99 | 100,000 | Unlimited | White-label, phone support, 25 team members |
| **Enterprise** | $199+ | 1M+ | Unlimited | SSO, dedicated support, custom integrations |

---

## 📚 Additional Resources

- **API Base URL:** `http://localhost:8000` (development)
- **Frontend URL:** Configured via `FRONTEND_URL` environment variable
- **Support:** Community forum, email support (paid plans), phone support (Business+)

---

**Last Updated:** October 23, 2025  
**API Version:** 1.0.0  
**Documentation Version:** 1.0.0
