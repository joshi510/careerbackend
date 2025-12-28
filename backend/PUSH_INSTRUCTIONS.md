# How to Push Backend to GitHub

## ⚠️ Important: Git Must Be Installed First

I cannot directly push to GitHub because:
1. Git is not installed on your system
2. GitHub authentication is required

## Quick Solution

### Option 1: Use the PowerShell Script (Easiest)

1. **Install Git** (if not installed):
   - Download from: https://git-scm.com/download/win
   - Run the installer
   - **Restart your computer** after installation

2. **Run the script**:
   - Open PowerShell
   - Navigate to backend folder:
     ```powershell
     cd C:\Users\Admin\Desktop\finalproject\backend
     ```
   - Run the script:
     ```powershell
     .\push-to-github.ps1
     ```

3. **When prompted for credentials**:
   - Username: Your GitHub username
   - Password: Use a **Personal Access Token** (not your GitHub password)
   - Get token from: https://github.com/settings/tokens
   - Create token with `repo` permissions

### Option 2: Manual Commands

After installing Git, open PowerShell in the `backend` folder and run:

```powershell
# Navigate to backend folder
cd C:\Users\Admin\Desktop\finalproject\backend

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Career Profiling Backend API"

# Add remote
git remote add origin https://github.com/joshi510/careerbackend.git

# Set branch to main
git branch -M main

# Push (you'll be prompted for credentials)
git push -u origin main
```

### Option 3: Use GitHub Desktop (GUI - Easiest)

1. **Download GitHub Desktop**: https://desktop.github.com/
2. **Install and sign in** with your GitHub account
3. **Add Local Repository**:
   - File → Add Local Repository
   - Browse to: `C:\Users\Admin\Desktop\finalproject\backend`
   - Click "Add"
4. **Publish Repository**:
   - Click "Publish repository" button
   - Repository name: `careerbackend`
   - Owner: `joshi510`
   - Click "Publish Repository"

## Generate Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "Backend Deployment"
4. Select scope: `repo` (check the box)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again)
7. Use this token as your password when pushing

## Verify Push

After pushing, check:
- https://github.com/joshi510/careerbackend
- You should see all your backend files
- Files should include: `main.py`, `requirements.txt`, `render.yaml`, etc.

## Next Steps After Push

1. **Deploy to Render**: Follow `RENDER_DEPLOYMENT.md`
2. **Set Environment Variables** in Render
3. **Test your API**

## Troubleshooting

### "Git is not recognized"
- Git is not installed or not in PATH
- Install Git and restart PowerShell
- Or use GitHub Desktop

### "Authentication failed"
- Use Personal Access Token, not password
- Ensure token has `repo` permissions
- Token might be expired - generate new one

### "Repository not found"
- Verify repository URL is correct
- Check you have push access
- Ensure repository exists on GitHub

## Need Help?

- Git Installation: https://git-scm.com/download/win
- GitHub Desktop: https://desktop.github.com/
- GitHub Tokens: https://github.com/settings/tokens

