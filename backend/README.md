# Career Profiling Platform - Backend API

FastAPI backend for the Career Profiling Platform.

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL/MySQL** - Database (supports both)
- **JWT** - Authentication
- **Google Gemini AI** - Career interpretation

## Setup

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file):
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=career_profiling_db
JWT_SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-gemini-api-key
DEBUG=true
```

3. Run the server:
```bash
uvicorn main:app --reload --port 8001
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Deployment on Render

This backend is configured for deployment on Render.com.

### Quick Deploy:

1. Push this repository to GitHub
2. Connect to Render
3. Create PostgreSQL database
4. Create Web Service pointing to this repo
5. Set environment variables (see `RENDER_DEPLOYMENT.md`)

For detailed deployment instructions, see `RENDER_DEPLOYMENT.md`.

## Environment Variables

### Required:
- `DATABASE_URL` - Database connection string (auto-provided by Render for PostgreSQL)
- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `GEMINI_API_KEY` - Google Gemini API key

### Optional:
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - MySQL configuration (if not using DATABASE_URL)
- `FRONTEND_URL` - Frontend URL for CORS (defaults to "*")
- `DEBUG` - Debug mode (default: false)

## Project Structure

```
backend/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration settings
├── database.py          # Database connection (supports PostgreSQL & MySQL)
├── models/              # SQLAlchemy models
├── routes/              # API route handlers
├── services/            # Business logic services
└── requirements.txt     # Python dependencies
```

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user

### Tests
- `POST /test/start` - Start a test
- `GET /test/status` - Get test status
- `GET /test/questions` - Get all questions
- `GET /test/sections/{id}/questions` - Get section questions
- `POST /test/sections/{id}/submit` - Submit section
- `POST /test/{id}/complete` - Complete test
- `GET /test/interpretation/{id}` - Get test interpretation

### Results
- `GET /student/result/{id}` - Get student result
- `GET /student/results` - Get all student results

## License

MIT

