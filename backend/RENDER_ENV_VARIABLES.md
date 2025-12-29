# Render Environment Variables - Exact Values to Enter

## Step-by-Step: Setting Environment Variables in Render

### 1. DATABASE_URL

**Where to get it:**
1. In Render dashboard, go to your **PostgreSQL database** service
2. Click on the database name
3. Go to **"Info"** tab
4. Find **"Internal Database URL"** (NOT External URL)
5. Copy the entire URL

**Example format:**
```
postgresql://career_profiling_user:password@dpg-xxxxx-a/career_profiling_db
```

**What to enter in Render:**
- **Key**: `DATABASE_URL`
- **Value**: Paste the Internal Database URL you copied
- **Important**: Use the **Internal** URL, not External

---

### 2. JWT_SECRET_KEY

**How to generate:**
You can generate a secure random string using one of these methods:

**Option A: Using Python (if you have Python installed):**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Option B: Using PowerShell:**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

**Option C: Online Generator:**
- Go to: https://generate-secret.vercel.app/32
- Click "Generate"
- Copy the generated string

**What to enter in Render:**
- **Key**: `JWT_SECRET_KEY`
- **Value**: Paste the generated random string (should be 32+ characters)
- **Example**: `aB3xY9mN2pQ7rT5vW8zA1cD4fG6hJ0kL3nM9oP2qR5sT8uV1wX4yZ7`

**⚠️ Important**: Keep this secret! Don't share it publicly.

---

### 3. GEMINI_API_KEY

**How to get it:**
1. Go to: https://makersuite.google.com/app/apikey
   OR: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"** or **"Get API Key"**
4. Copy the API key (starts with `AIza...`)

**What to enter in Render:**
- **Key**: `GEMINI_API_KEY`
- **Value**: Paste your Gemini API key
- **Example**: `AIzaSyB1234567890abcdefghijklmnopqrstuvwxyz`

**⚠️ Important**: Keep this secret! Don't share it publicly.

---

### 4. DEBUG

**What to enter in Render:**
- **Key**: `DEBUG`
- **Value**: `false` (always use lowercase)
- **Purpose**: Disables debug mode for production

---

### 5. FRONTEND_URL (Optional - Only if you have a frontend)

**What to enter in Render:**
- **Key**: `FRONTEND_URL`
- **Value**: Your frontend URL (if you have one deployed)
- **Example**: `https://your-frontend.onrender.com`
- **If no frontend yet**: You can skip this or set to `*`

---

## Complete Example - All Variables

Here's what your Environment Variables section should look like in Render:

```
DATABASE_URL = postgresql://career_profiling_user:abc123@dpg-xxxxx-a.singapore-postgres.render.com/career_profiling_db
JWT_SECRET_KEY = aB3xY9mN2pQ7rT5vW8zA1cD4fG6hJ0kL3nM9oP2qR5sT8uV1wX4yZ7
GEMINI_API_KEY = AIzaSyB1234567890abcdefghijklmnopqrstuvwxyz
DEBUG = false
FRONTEND_URL = *
```

---

## How to Add in Render Dashboard

1. Go to your **Web Service** in Render
2. Click on the service name
3. Go to **"Environment"** tab (left sidebar)
4. Click **"Add Environment Variable"** button
5. Enter **Key** and **Value** for each variable
6. Click **"Save Changes"** after adding all variables

---

## Quick Checklist

- [ ] DATABASE_URL - From PostgreSQL service (Internal URL)
- [ ] JWT_SECRET_KEY - Generated random string (32+ chars)
- [ ] GEMINI_API_KEY - From Google AI Studio
- [ ] DEBUG - Set to `false`
- [ ] FRONTEND_URL - Optional (set to `*` if no frontend)

---

## Troubleshooting

### "Invalid DATABASE_URL"
- Make sure you copied the **Internal** URL, not External
- Check the URL starts with `postgresql://` or `postgres://`
- Verify database service is running

### "JWT_SECRET_KEY too short"
- Generate a longer key (at least 32 characters)
- Use the Python command or online generator

### "Invalid GEMINI_API_KEY"
- Verify you copied the entire key
- Check it starts with `AIza`
- Make sure there are no extra spaces

### "Can't connect to database"
- Verify DATABASE_URL is correct
- Check database service is running
- Ensure using Internal URL (not External)

---

## Security Notes

⚠️ **Never commit these values to GitHub!**
- These are secrets and should only be in Render environment variables
- The `.gitignore` file already excludes `.env` files
- Always use environment variables, never hardcode secrets

