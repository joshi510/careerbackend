# Deploy Backend to Render

This guide will help you deploy the Career Profiling Backend API to Render.

## Prerequisites

1. **GitHub Repository**: Code pushed to https://github.com/joshi510/careerbackend
2. **Render Account**: Sign up at https://render.com
3. **Gemini API Key**: Get from https://makersuite.google.com/app/apikey

## Step-by-Step Deployment

### Step 1: Create PostgreSQL Database

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `career-profiling-db`
   - **Database**: `career_profiling_db`
   - **User**: `career_profiling_user`
   - **Region**: Choose closest to your users
   - **Plan**: Free (or paid for production)
4. Click **"Create Database"**
5. **IMPORTANT**: Note the **Internal Database URL** (you'll need this)

### Step 2: Deploy Backend Web Service

#### Option A: Using render.yaml (Recommended)

1. Make sure `render.yaml` is in the `backend/` folder
2. In Render dashboard, click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository: `https://github.com/joshi510/careerbackend`
4. Render will automatically detect `render.yaml` and create services
5. You'll still need to set `GEMINI_API_KEY` and `FRONTEND_URL` manually

#### Option B: Manual Setup

1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `https://github.com/joshi510/careerbackend`
3. Configure the service:
   - **Name**: `career-profiling-api`
   - **Environment**: `Python 3`
   - **Region**: Same as database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `backend` (important!)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Click **"Create Web Service"**

### Step 3: Configure Environment Variables

Go to your Web Service → **"Environment"** tab and add:

#### Required Variables:
```
DATABASE_URL=<Internal Database URL from Step 1>
JWT_SECRET_KEY=<Generate a strong random string>
GEMINI_API_KEY=<Your Gemini API key>
```

#### Optional Variables:
```
DEBUG=false
FRONTEND_URL=<Your frontend URL if you have one>
```

#### Generate JWT Secret Key:
You can generate a secure key using:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Or use an online generator: https://generate-secret.vercel.app/32

### Step 4: Deploy

1. Click **"Manual Deploy"** → **"Deploy latest commit"**
2. Wait for deployment (5-10 minutes)
3. Check **"Logs"** tab for any errors

### Step 5: Verify Deployment

1. Once deployed, you'll get a URL like: `https://career-profiling-api.onrender.com`
2. Test the API:
   - Health check: `https://your-api-url.onrender.com/docs`
   - API docs: `https://your-api-url.onrender.com/docs`
   - ReDoc: `https://your-api-url.onrender.com/redoc`

## Important Notes

### Root Directory
Since your backend code is in the `backend/` folder, make sure to set:
- **Root Directory**: `backend` in Render settings

### Database Connection
- Render automatically provides `DATABASE_URL` for PostgreSQL
- The code supports both PostgreSQL (via `DATABASE_URL`) and MySQL (via individual env vars)
- For Render, use the Internal Database URL (not External)

### CORS Configuration
- If you have a frontend, set `FRONTEND_URL` environment variable
- The backend will allow CORS from that URL
- If not set, it defaults to allowing all origins (`*`)

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `JWT_SECRET_KEY` | Yes | Secret for JWT tokens | Generated random string |
| `GEMINI_API_KEY` | Yes | Google Gemini API key | `AIza...` |
| `DEBUG` | No | Debug mode | `false` |
| `FRONTEND_URL` | No | Frontend URL for CORS | `https://your-frontend.com` |

## Troubleshooting

### Build Fails
- Check Python version matches `runtime.txt` (3.11.0)
- Verify all dependencies in `requirements.txt`
- Check build logs for specific errors

### Database Connection Error
- Verify `DATABASE_URL` is correct
- Ensure using Internal Database URL (not External)
- Check database is running
- Verify database user has proper permissions

### Application Won't Start
- Check start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Verify `main.py` exists in root directory
- Check logs for import errors

### Port Issues
- Always use `$PORT` variable in start command
- Render automatically assigns port

## Monitoring

- **Logs**: Real-time logs in Render dashboard
- **Metrics**: Performance metrics in Metrics tab
- **Alerts**: Set up alerts for downtime

## Cost

**Free Tier**:
- 750 hours/month free
- 90 days PostgreSQL trial

**Paid Plans** (Production):
- Web Service: $7/month (Starter)
- PostgreSQL: $7/month (Starter)

## Next Steps

After backend is deployed:
1. Note your API URL
2. Update frontend `VITE_API_URL` to point to this backend
3. Test all endpoints
4. Set up monitoring and alerts

## Support

- Render Docs: https://render.com/docs
- FastAPI Docs: https://fastapi.tiangolo.com
- Render Status: https://status.render.com

