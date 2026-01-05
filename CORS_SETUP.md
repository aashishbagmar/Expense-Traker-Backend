# Backend CORS Configuration for Railway

## Quick Fix for Django Backend

Add this to your `backend/backend/settings.py`:

```python
# CORS Configuration for Vercel Frontend
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'corsheaders',  # ← Add this
    
    # Your apps
    'users',
    'transactions',
    # ... other apps
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ← Add this at the TOP
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... rest of middleware
]

# Replace with your actual Vercel deployment URL
CORS_ALLOWED_ORIGINS = [
    "https://expense-tracker-frontend.vercel.app",
]

# If using preview deployments, add pattern or use:
# CORS_ALLOWED_ORIGIN_REGEXES = [
#     r"^https://.*\.vercel\.app$",
# ]

CORS_ALLOW_CREDENTIALS = True
```

## Install django-cors-headers if not already installed

```bash
pip install django-cors-headers
```

Then update `requirements.txt`:
```bash
pip freeze > requirements.txt
```

## Push to Railway

```bash
git add .
git commit -m "feat: add CORS support for Vercel frontend"
git push origin main
```

Railway will automatically redeploy with the new CORS settings.

---

## Testing CORS

After deploying, test by:

1. Opening your Vercel frontend URL
2. Open browser DevTools → Network tab
3. Try to login
4. Check response headers should include:
   ```
   Access-Control-Allow-Origin: https://expense-tracker-frontend.vercel.app
   Access-Control-Allow-Credentials: true
   ```

If you see CORS errors, check:
- [ ] `corsheaders` is installed
- [ ] `CorsMiddleware` is **first** in MIDDLEWARE list
- [ ] Your Vercel URL is in `CORS_ALLOWED_ORIGINS`
- [ ] Railway has redeployed with the changes
