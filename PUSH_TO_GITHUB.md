# Push Backend to GitHub Repository

This guide will help you push your backend code to https://github.com/joshi510/careerbackend

## Prerequisites

1. **Git Installed**: Download from https://git-scm.com/download/win if not installed
2. **GitHub Account**: You already have the repository created
3. **Backend Code**: All files are in the `backend/` folder

## Step-by-Step Instructions

### Step 1: Navigate to Backend Folder

Open PowerShell/Terminal and navigate to your backend folder:

```bash
cd C:\Users\Admin\Desktop\finalproject\backend
```

### Step 2: Initialize Git Repository

```bash
git init
```

### Step 3: Add All Files

```bash
git add .
```

### Step 4: Create Initial Commit

```bash
git commit -m "Initial commit: Career Profiling Backend API"
```

### Step 5: Add Remote Repository

```bash
git remote add origin https://github.com/joshi510/careerbackend.git
```

### Step 6: Rename Branch to Main

```bash
git branch -M main
```

### Step 7: Push to GitHub

```bash
git push -u origin main
```

## Authentication

GitHub will ask for authentication. You have two options:

### Option A: Personal Access Token (Recommended)

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name and select `repo` scope
4. Copy the token
5. When prompted for password, paste the token

### Option B: GitHub Desktop

1. Download GitHub Desktop: https://desktop.github.com/
2. Sign in with your GitHub account
3. File → Add Local Repository → Select your `backend` folder
4. Click "Publish repository"

## Verify Push

1. Go to https://github.com/joshi510/careerbackend
2. You should see all your backend files
3. Check that these files are present:
   - `main.py`
   - `requirements.txt`
   - `render.yaml`
   - `Procfile`
   - `runtime.txt`
   - `README.md`
   - All folders: `models/`, `routes/`, `services/`, etc.

## Next Steps

After pushing to GitHub:

1. **Deploy to Render**: Follow `RENDER_DEPLOYMENT.md`
2. **Set Environment Variables**: Configure in Render dashboard
3. **Test Deployment**: Verify API is working

## Troubleshooting

### "Repository not found" error
- Verify repository URL is correct
- Check you have push access to the repository
- Ensure repository exists on GitHub

### "Authentication failed"
- Use Personal Access Token instead of password
- Check token has `repo` permissions
- Regenerate token if expired

### "Nothing to commit"
- Check you're in the `backend` folder
- Verify files exist: `ls` (Linux/Mac) or `dir` (Windows)
- Make sure `.gitignore` isn't excluding everything

## Quick Command Summary

```bash
cd backend
git init
git add .
git commit -m "Initial commit: Career Profiling Backend API"
git remote add origin https://github.com/joshi510/careerbackend.git
git branch -M main
git push -u origin main
```

