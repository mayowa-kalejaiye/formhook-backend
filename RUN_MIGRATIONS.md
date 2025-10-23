# Database Migration Fix

## Problem
The production database is missing tables that the application expects:
- `webhook_delivery` table
- `email_log` table
- Possibly other tables from recent migrations

## Quick Fix Applied
✅ Added error handling to endpoints that query these tables:
- `/dashboard/summary` - Now returns empty webhook stats if table doesn't exist
- `/forms/{form_id}/analytics` - Now returns empty webhook/email stats if tables don't exist

## Permanent Solution: Run Database Migrations

### On Render (Production)

1. **SSH into your Render instance** or use the Render Shell:
   ```bash
   # In Render Dashboard -> Shell
   cd /opt/render/project/src
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Verify migrations**:
   ```bash
   alembic current
   alembic history
   ```

### Locally (Development)

**Note:** Your local database is already up to date! Current migration: `20250901_add_email_verification`

If you need to run migrations locally in the future:

1. **Ensure you're in the project root**:
   ```cmd
   cd c:\Users\kalej\Documents\formhook-backend
   ```

2. **Install dependencies** (if not already installed):
   ```cmd
   C:/Python313/python.exe -m pip install -r requirements.txt
   ```

3. **Check current migration status**:
   ```cmd
   C:/Python313/python.exe -m alembic current
   ```

4. **Run migrations**:
   ```cmd
   C:/Python313/python.exe -m alembic upgrade head
   ```

## Migration Files to Apply

The following migrations need to be applied:

1. ✅ `caeeba6612ba` - Create users table
2. ✅ `ebc97af20988` - Create forms table
3. ✅ `0355395e236c` - Create submissions table
4. ✅ `3a3d99b1a060` - **Create webhook_delivery table** ⚠️
5. ✅ `b640d1182475` - Add webhook headers and secret
6. ✅ `ca5212d09bc8` - Add API token hash
7. ✅ `20250801` - Add geolocation fields
8. ✅ `20250901` - **Add email verification** (creates email_log table) ⚠️
9. ✅ `add_user_subscription_fields` - Add subscription tracking

## Check Current Migration Status

```bash
# See which migrations have been applied
alembic current

# See migration history
alembic history --verbose

# See pending migrations
alembic upgrade head --sql
```

## Rollback (If Needed)

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

## Troubleshooting

### Error: "Can't locate revision identified by..."
This means Alembic can't find the migration files. Ensure:
- You're in the correct directory
- `alembic.ini` exists
- `migrations/versions/` folder has all migration files

### Error: "Target database is not up to date"
Run:
```bash
alembic stamp head
```

### Error: "relation already exists"
The table already exists. Skip that migration:
```bash
alembic stamp <revision_id>
alembic upgrade head
```

## After Running Migrations

1. **Restart your Render service** to ensure all processes use the new schema
2. **Test the endpoints** that were failing:
   - `GET /dashboard/summary`
   - `GET /forms/{form_id}/analytics`
3. **Remove error handling** from the code (optional, but recommended for proper error reporting)

## Prevention

Add this to your Render deployment script in `render.yaml`:

```yaml
services:
  - type: web
    name: formhook-backend
    env: python
    buildCommand: "pip install -r requirements.txt && alembic upgrade head"
    startCommand: "uvicorn formhook.app.main:app --host 0.0.0.0 --port $PORT"
```

This ensures migrations run automatically on every deployment.
