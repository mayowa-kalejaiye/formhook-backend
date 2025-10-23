# 🚨 URGENT: Run Migrations on Render

Your **production database on Render** is missing required tables. This is why the frontend is getting 500 errors.

## ✅ Your Local Database
Your local database is **already up to date** at migration: `20250901_add_email_verification`

## ❌ Your Production Database (Render)
Missing tables:
- `webhook_delivery` table
- `email_log` table

## 🔧 Fix: Run Migrations on Render

### ✅ Easy Fix: Push Changes to GitHub (Free Tier Compatible!)

Since you're on the free tier and can't use SSH/Shell, just push your code and let Render auto-deploy:

**Step 1: Commit and push your changes**

```cmd
git add .
git commit -m "Add automatic migrations on deployment"
git push origin main
```

**Step 2: Render will automatically:**
- Pull your latest code
- Run `pip install -r requirements.txt && alembic upgrade head` (from render.yaml)
- Apply all missing migrations
- Start your app

**That's it!** The migrations will run automatically on every deployment.

### Alternative: Update Build Command in Render Dashboard

Update your Render service settings:

1. Go to **Settings** in Render Dashboard
2. Find **Build Command**
3. Change from:
   ```bash
   pip install -r requirements.txt
   ```
   
   To:
   ```bash
   pip install -r requirements.txt && alembic upgrade head
   ```

4. **Save Changes**
5. Click **Manual Deploy** to trigger a new deployment

This will run migrations automatically on every deployment!

## ✅ Verification

After running migrations, test these endpoints:

1. **Dashboard**: `GET https://your-render-url.onrender.com/dashboard/summary`
2. **Analytics**: `GET https://your-render-url.onrender.com/forms/{form_id}/analytics`

Both should return 200 OK instead of 500 errors.

## 📝 Migration Status

Expected migration after running `alembic upgrade head`:

```
20250901_add_email_verification (head)
```

This includes all these migrations:
- ✅ Create users table
- ✅ Add API token hash
- ✅ Add webhook headers
- ✅ Create forms table
- ✅ Create webhook_delivery table ← **NEEDED FOR DASHBOARD**
- ✅ Create submissions table
- ✅ Add API token to forms
- ✅ Add geolocation fields
- ✅ Add email verification ← **NEEDED FOR ANALYTICS**

## 🆘 Troubleshooting

### Error: "alembic: command not found"
The dependencies might not be installed. Run:
```bash
pip install -r requirements.txt
```

### Error: "Can't connect to database"
Check your `DATABASE_URL` environment variable in Render settings.

### Error: "relation already exists"
Some migrations were already applied. This is OK - alembic will skip them.

## ⚡ Quick Test

Once migrations are done, the frontend should stop showing errors and you'll see:
- Dashboard stats loading correctly
- Form analytics showing webhook/email data
- No more 500 Internal Server Error messages

---

**Status**: 
- 🟢 Local: Up to date
- 🔴 Production (Render): **NEEDS MIGRATION** ← Run `alembic upgrade head` in Render Shell
