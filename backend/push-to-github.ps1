# PowerShell script to push backend to GitHub
# Run this script from the backend folder

Write-Host "🚀 Pushing backend to GitHub..." -ForegroundColor Green

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "✅ Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git is not installed!" -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "After installation, restart PowerShell and run this script again." -ForegroundColor Yellow
    exit 1
}

# Initialize git repository if not already initialized
if (-not (Test-Path .git)) {
    Write-Host "📦 Initializing git repository..." -ForegroundColor Cyan
    git init
} else {
    Write-Host "✅ Git repository already initialized" -ForegroundColor Green
}

# Add all files
Write-Host "📝 Adding all files..." -ForegroundColor Cyan
git add .

# Check if there are changes to commit
$status = git status --porcelain
if ($status) {
    Write-Host "💾 Committing changes..." -ForegroundColor Cyan
    git commit -m "Initial commit: Career Profiling Backend API"
} else {
    Write-Host "ℹ️  No changes to commit" -ForegroundColor Yellow
}

# Check if remote exists
$remote = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "🔗 Adding remote repository..." -ForegroundColor Cyan
    git remote add origin https://github.com/joshi510/careerbackend.git
} else {
    Write-Host "✅ Remote already configured: $remote" -ForegroundColor Green
    $update = Read-Host "Update remote URL? (y/n)"
    if ($update -eq "y") {
        git remote set-url origin https://github.com/joshi510/careerbackend.git
    }
}

# Rename branch to main
Write-Host "🌿 Setting branch to main..." -ForegroundColor Cyan
git branch -M main

# Push to GitHub
Write-Host "⬆️  Pushing to GitHub..." -ForegroundColor Cyan
Write-Host "⚠️  You will be prompted for GitHub credentials" -ForegroundColor Yellow
Write-Host "   Use your Personal Access Token as password" -ForegroundColor Yellow
Write-Host "   Get token from: https://github.com/settings/tokens" -ForegroundColor Yellow
Write-Host ""

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host "🔗 Repository: https://github.com/joshi510/careerbackend" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Push failed. Please check:" -ForegroundColor Red
    Write-Host "   1. GitHub credentials are correct" -ForegroundColor Yellow
    Write-Host "   2. You have push access to the repository" -ForegroundColor Yellow
    Write-Host "   3. Repository exists on GitHub" -ForegroundColor Yellow
}

