# 🚀 Quick Setup Guide: Push Notifications

## Prerequisites
- FormHook backend deployed
- Python 3.9+ installed
- Access to environment variables

---

## Step 1: Install Dependencies Locally

```bash
pip install pywebpush
```

---

## Step 2: Generate VAPID Keys

```bash
cd formhook-backend
python scripts/generate_vapid_keys.py
```

**Output:**
```
🔐 Generating VAPID keys for FormHook Push Notifications...
------------------------------------------------------------

✅ VAPID Keys Generated Successfully!

============================================================
Add these to your .env file:
============================================================

VAPID_PUBLIC_KEY=BEl62iUYgUivxIkv69yViEuiBIa-Ib...
VAPID_PRIVATE_KEY=bdSiGcITKnyQxqkWvOq3HEJP...
VAPID_SUBJECT=mailto:admin@formhook.com
```

---

## Step 3: Add Environment Variables

### Render Dashboard:
1. Go to your service dashboard
2. Navigate to "Environment" tab
3. Add three new variables:

```bash
VAPID_PUBLIC_KEY=<your_public_key>
VAPID_PRIVATE_KEY=<your_private_key>
VAPID_SUBJECT=mailto:admin@formhook.com
```

⚠️ **Important:**
- Replace `<your_public_key>` and `<your_private_key>` with the generated keys
- Change `admin@formhook.com` to your actual admin email
- Keep the private key **SECRET**

### Local .env file:
```bash
echo "VAPID_PUBLIC_KEY=<your_public_key>" >> .env
echo "VAPID_PRIVATE_KEY=<your_private_key>" >> .env
echo "VAPID_SUBJECT=mailto:admin@formhook.com" >> .env
```

---

## Step 4: Deploy

```bash
git add .
git commit -m "Add push notifications system"
git push origin main
```

**What happens on Render:**
1. ✅ Installs `pywebpush` from requirements.txt
2. ✅ Runs migration `5fadffbd2fe8` (creates push_subscriptions table)
3. ✅ Loads VAPID keys from environment
4. ✅ Starts 7 new endpoints at `/notifications/push/`

---

## Step 5: Verify Deployment

### Check migration applied:
```bash
# In Render shell or locally
python -m alembic current
```

Expected output: `5fadffbd2fe8 (head)`

### Test VAPID key endpoint:
```bash
curl https://your-backend.com/notifications/push/vapid-key
```

Expected response:
```json
{
  "publicKey": "BEl62iUYgUivxIkv69yViEuiBIa-Ib..."
}
```

---

## Step 6: Frontend Integration

The frontend will automatically:
1. Fetch VAPID public key from `/notifications/push/vapid-key`
2. Register service worker
3. Subscribe to push service
4. Send subscription to `/notifications/push/subscribe`

**No additional frontend changes needed!**

---

## 🧪 Testing

### 1. Subscribe (from browser):
Enable push notifications in FormHook UI → Check browser notification permission

### 2. Test notification:
```bash
curl -X POST https://your-backend.com/notifications/push/test \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Trigger real notification:
Submit a form → Should receive push notification

---

## 📊 Monitoring

### Check active subscriptions:
```bash
curl https://your-backend.com/notifications/push/subscriptions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check logs:
Look for messages like:
```
INFO: Push notification sent successfully to subscription 123
INFO: Deleted invalid subscription 456 (410 Gone)
```

---

## ✅ Success Checklist

- [ ] VAPID keys generated
- [ ] Environment variables added to Render
- [ ] Code deployed successfully
- [ ] Migration applied (5fadffbd2fe8)
- [ ] `/notifications/push/vapid-key` returns public key
- [ ] Test notification works
- [ ] Form submission triggers push notification
- [ ] Browser displays notification

---

## 🐛 Troubleshooting

### "VAPID keys not configured"
**Fix:** Verify environment variables are set on Render, restart service

### "Migration failed"
**Fix:** Check database connection, run manually: `alembic upgrade head`

### "Push not received"
**Fix:** 
1. Check browser console for errors
2. Verify service worker registered
3. Check notification permission granted
4. Test with `/notifications/push/test` endpoint

### "Invalid subscription"
**Fix:** Re-enable push notifications on frontend (creates new subscription)

---

## 🎉 You're Done!

Your users will now receive:
- ✅ New form submissions
- ✅ Webhook failures
- ✅ Security alerts
- ✅ Milestone achievements

Push notifications are sent to **all their devices** automatically! 🚀
