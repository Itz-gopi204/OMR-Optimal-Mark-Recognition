# OMR Evaluation System - Backend

Production-level OMR (Optical Mark Recognition) evaluation system backend built with FastAPI, MongoDB, and OpenCV.

## Features

- **Multi-tenant Architecture**: Support for multiple schools/universities with isolated data
- **Role-based Access Control**: Super Admin, Institution Admin, Teachers, Students, Parents
- **OMR Processing**: MCQ sheets, surveys, attendance tracking
- **Real-time Updates**: WebSocket support for live processing status
- **JWT Authentication**: Secure authentication with refresh tokens

## Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB with Beanie ODM
- **Cache/Queue**: Redis with Celery
- **Image Processing**: OpenCV, NumPy
- **Authentication**: JWT with python-jose

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB 6.0+
- Redis 7.0+

### Development Setup

1. **Clone and navigate to backend:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Start MongoDB and Redis:**
   ```bash
   # Using Docker
   docker run -d -p 27017:27017 --name mongo mongo:6
   docker run -d -p 6379:6379 --name redis redis:7-alpine
   ```

6. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

7. **Create super admin:**
   ```bash
   python scripts/create_superuser.py
   ```

### Docker Setup

```bash
# From project root
docker-compose up -d
```

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config/              # Configuration
│   │   ├── settings.py      # App settings
│   │   └── database.py      # MongoDB connection
│   ├── api/v1/              # API endpoints
│   │   ├── auth/            # Authentication
│   │   ├── users/           # User management
│   │   ├── institutions/    # Institution management
│   │   ├── templates/       # OMR templates
│   │   ├── tests/           # Tests/exams
│   │   └── sheets/          # OMR sheets
│   ├── models/              # MongoDB models
│   ├── core/                # Core utilities
│   │   ├── security.py      # JWT authentication
│   │   └── permissions.py   # RBAC
│   ├── omr/                 # OMR processing
│   │   └── processor.py     # OpenCV processor
│   └── workers/             # Celery tasks
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users` - List users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Institutions (Super Admin)
- `GET /api/v1/admin/institutions` - List institutions
- `POST /api/v1/admin/institutions` - Create institution
- `GET /api/v1/admin/institutions/{id}` - Get institution
- `PUT /api/v1/admin/institutions/{id}` - Update institution

### Templates
- `GET /api/v1/templates` - List templates
- `POST /api/v1/templates` - Create template
- `POST /api/v1/templates/{id}/calibrate` - Calibrate template

### Tests
- `GET /api/v1/tests` - List tests
- `POST /api/v1/tests` - Create test
- `PUT /api/v1/tests/{id}/answer-key` - Set answer key
- `POST /api/v1/tests/{id}/publish` - Publish results

### Sheets
- `POST /api/v1/sheets/upload` - Upload sheet
- `POST /api/v1/sheets/upload/bulk` - Bulk upload
- `POST /api/v1/sheets/{id}/process` - Process sheet

## Environment Variables

See `.env.example` for all available configuration options.

## Running Tests

```bash
pytest
```

## License

MIT
