# Quick Start: Deploy Backend to Render

## 🚀 Fast Track Deployment

### 1. Push to GitHub (5 minutes)

```bash
cd backend
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/joshi510/careerbackend.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render (10 minutes)

1. **Go to**: https://dashboard.render.com
2. **Click**: "New +" → "PostgreSQL"
3. **Create Database**:
   - Name: `career-profiling-db`
   - Plan: Free
   - Click "Create"
4. **Click**: "New +" → "Web Service"
5. **Connect**: Your GitHub repo `joshi510/careerbackend`
6. **Configure**:
   - Name: `career-profiling-api`
   - Root Directory: `backend` ⚠️ **IMPORTANT**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. **Environment Variables**:
   - `DATABASE_URL` → Copy from PostgreSQL service (Internal URL)
   - `JWT_SECRET_KEY` → Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `GEMINI_API_KEY` → Your API key from https://makersuite.google.com/app/apikey
   - `DEBUG` → `false`
8. **Deploy**: Click "Create Web Service"

### 3. Test (2 minutes)

1. Wait for deployment (5-10 minutes)
2. Visit: `https://your-api-name.onrender.com/docs`
3. You should see Swagger UI with all API endpoints

## ✅ Checklist

- [ ] Code pushed to GitHub
- [ ] PostgreSQL database created
- [ ] Web service created
- [ ] Root directory set to `backend`
- [ ] Environment variables configured
- [ ] Deployment successful
- [ ] API docs accessible

## 🆘 Need Help?

- See `RENDER_DEPLOYMENT.md` for detailed instructions
- Check Render logs if deployment fails
- Verify all environment variables are set

## 📝 Important Notes

- **Root Directory**: Must be `backend` (not root of repo)
- **Database URL**: Use Internal URL (not External)
- **Port**: Always use `$PORT` variable in start command
- **API Key**: Get from Google AI Studio

