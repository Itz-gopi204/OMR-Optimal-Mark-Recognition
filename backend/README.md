# OMR Evaluation System - Backend API

A production-grade, multi-tenant OMR (Optical Mark Recognition) evaluation system backend built with **FastAPI**, **MongoDB**, and **OpenCV**. Designed for schools, universities, and coaching institutes to automate answer sheet evaluation.

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Docker Setup](#docker-setup)
- [Configuration](#configuration)
- [Database Models](#database-models)
- [API Reference](#api-reference)
- [Authentication & Authorization](#authentication--authorization)
- [OMR Processing Pipeline](#omr-processing-pipeline)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Features

### Core Functionality
- **Multi-tenant Architecture** - Complete data isolation between institutions
- **OMR Sheet Processing** - Automated bubble detection and answer extraction using OpenCV
- **Multiple Sheet Types** - MCQ answer sheets, surveys, feedback forms, attendance
- **Batch Processing** - Upload and process hundreds of sheets at once
- **Real-time Updates** - WebSocket support for live processing status

### User Management
- **Role-based Access Control (RBAC)** - 5 user roles with 25+ granular permissions
- **JWT Authentication** - Secure token-based auth with refresh tokens
- **OAuth Integration** - Google and Microsoft login support (configurable)
- **Bulk User Import** - CSV upload for mass user creation

### Academic Features
- **Test Management** - Create tests with configurable marking schemes
- **Answer Key Management** - Support for multiple correct answers
- **Negative Marking** - Configurable penalty for wrong answers
- **Result Analytics** - Statistics, rankings, and performance insights
- **Export Options** - CSV and PDF export for results

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | FastAPI 0.109 | High-performance async API |
| **Database** | MongoDB 6.0 | Document storage with Beanie ODM |
| **Cache** | Redis 7.0 | Caching and message broker |
| **Task Queue** | Celery 5.3 | Background job processing |
| **Image Processing** | OpenCV 4.9 | OMR detection and analysis |
| **Authentication** | python-jose | JWT token handling |
| **Validation** | Pydantic 2.5 | Data validation and serialization |
| **File Storage** | MinIO/S3 | Scalable object storage |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                    │
│              (Web App, Mobile App, Scanner Integration)              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        LOAD BALANCER                                 │
│                      (Nginx / AWS ALB)                               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │  FastAPI  │   │  FastAPI  │   │ WebSocket │
        │  Server   │   │  Server   │   │  Server   │
        └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   MongoDB     │     │    Redis      │     │  MinIO/S3     │
│  (Primary DB) │     │ (Cache/Queue) │     │  (Storage)    │
└───────────────┘     └───────┬───────┘     └───────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │ Celery Worker │
                      │ (OMR Process) │
                      └───────────────┘
```

---

## Project Structure

```
backend/
│
├── app/                            # Main application package
│   ├── __init__.py
│   ├── main.py                     # FastAPI app initialization & lifespan
│   │
│   ├── config/                     # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py             # Environment-based settings (Pydantic)
│   │   ├── database.py             # MongoDB connection & Beanie setup
│   │   └── redis.py                # Redis connection (TODO)
│   │
│   ├── api/                        # API layer
│   │   ├── __init__.py
│   │   └── v1/                     # API version 1
│   │       ├── __init__.py
│   │       ├── router.py           # Main router aggregating all endpoints
│   │       │
│   │       ├── auth/               # Authentication endpoints
│   │       │   ├── __init__.py
│   │       │   ├── router.py       # POST /login, /register, /refresh
│   │       │   ├── schemas.py      # LoginRequest, TokenResponse, etc.
│   │       │   └── service.py      # AuthService business logic
│   │       │
│   │       ├── users/              # User management endpoints
│   │       │   ├── __init__.py
│   │       │   ├── router.py       # CRUD + bulk import + stats
│   │       │   ├── schemas.py      # UserCreate, UserUpdate, UserResponse
│   │       │   └── service.py      # UserService with tenant scoping
│   │       │
│   │       ├── institutions/       # Institution management (Super Admin)
│   │       │   ├── __init__.py
│   │       │   ├── router.py       # CRUD for institutions
│   │       │   ├── schemas.py      # Institution schemas
│   │       │   └── service.py      # InstitutionService
│   │       │
│   │       ├── templates/          # OMR template management
│   │       │   └── __init__.py     # (Endpoints pending)
│   │       │
│   │       ├── tests/              # Test/exam management
│   │       │   └── __init__.py     # (Endpoints pending)
│   │       │
│   │       └── sheets/             # OMR sheet processing
│   │           └── __init__.py     # (Endpoints pending)
│   │
│   ├── models/                     # MongoDB document models (Beanie)
│   │   ├── __init__.py             # Model exports
│   │   ├── base.py                 # BaseDocument with timestamps
│   │   ├── institution.py          # Institution, Subscription, Settings
│   │   ├── user.py                 # User, UserProfile, UserRole
│   │   ├── omr_template.py         # OMRTemplate, TemplateConfig
│   │   ├── test.py                 # Test, AnswerKey, MarkingScheme
│   │   └── omr_sheet.py            # OMRSheet, ProcessingResult, Evaluation
│   │
│   ├── core/                       # Core utilities & middleware
│   │   ├── __init__.py
│   │   ├── security.py             # JWT creation/verification, password hash
│   │   ├── permissions.py          # RBAC: Permission enum, role mappings
│   │   └── exceptions.py           # Custom HTTP exceptions
│   │
│   ├── omr/                        # OMR processing engine
│   │   ├── __init__.py
│   │   ├── processor.py            # Main OMRProcessor class (OpenCV)
│   │   ├── detection/              # Detection modules
│   │   │   └── __init__.py
│   │   └── evaluation/             # Evaluation modules
│   │       └── __init__.py
│   │
│   ├── services/                   # Business services
│   │   └── __init__.py             # Storage, Email, Notification (TODO)
│   │
│   ├── workers/                    # Celery background workers
│   │   ├── __init__.py
│   │   └── tasks/                  # Task definitions
│   │       └── __init__.py
│   │
│   └── utils/                      # Utility functions
│       └── __init__.py
│
├── scripts/                        # CLI scripts
│   └── create_superuser.py         # Interactive super admin creation
│
├── tests/                          # Test suite (pytest)
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── e2e/                        # End-to-end tests
│
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container image definition
├── .env.example                    # Environment template
└── README.md                       # This file
```

---

## Getting Started

### Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Runtime |
| MongoDB | 6.0+ | Database |
| Redis | 7.0+ | Cache & Queue |
| Docker | 24.0+ | Containerization (optional) |

### Installation

#### 1. Clone and navigate to backend
```bash
cd backend
```

#### 2. Create and activate virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure environment
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` with your configuration (see [Configuration](#configuration))

#### 5. Start required services

**Option A: Using Docker (Recommended)**
```bash
docker run -d --name omr-mongo -p 27017:27017 mongo:6
docker run -d --name omr-redis -p 6379:6379 redis:7-alpine
```

**Option B: Local installation**
- Install MongoDB: https://www.mongodb.com/docs/manual/installation/
- Install Redis: https://redis.io/docs/getting-started/

#### 6. Run the application
```bash
# Development with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 7. Create super admin user
```bash
python scripts/create_superuser.py
```

#### 8. Access the API
- **API Base URL**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

### Docker Setup

For a complete containerized setup, use Docker Compose from the project root:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

Services started:
- `omr-api` - FastAPI backend (port 8000)
- `omr-worker` - Celery worker
- `omr-mongo` - MongoDB (port 27017)
- `omr-redis` - Redis (port 6379)
- `omr-minio` - MinIO storage (ports 9000, 9001)

---

## Configuration

All configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | OMR Evaluation System | Application name |
| `DEBUG` | false | Enable debug mode |
| `ENVIRONMENT` | production | Environment (development/staging/production) |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Server bind address |
| `PORT` | 8000 | Server port |
| `CORS_ORIGINS` | http://localhost:3000 | Allowed CORS origins (comma-separated) |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | mongodb://localhost:27017 | MongoDB connection string |
| `MONGODB_DATABASE` | omr_evaluation | Database name |
| `REDIS_URL` | redis://localhost:6379 | Redis connection string |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (required) | JWT signing key (use `openssl rand -hex 32`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime |

### File Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_TYPE` | local | Storage backend (local/s3) |
| `UPLOAD_DIR` | uploads | Local upload directory |
| `S3_ENDPOINT` | - | S3/MinIO endpoint URL |
| `S3_ACCESS_KEY` | - | S3 access key |
| `S3_SECRET_KEY` | - | S3 secret key |
| `S3_BUCKET` | omr-sheets | S3 bucket name |

### OMR Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `OMR_CONFIDENCE_THRESHOLD` | 0.7 | Minimum confidence for detection |
| `OMR_FILL_THRESHOLD` | 0.4 | Bubble fill percentage threshold |

---

## Database Models

### Entity Relationship

```
┌─────────────────┐       ┌─────────────────┐
│   Institution   │       │      User       │
│─────────────────│       │─────────────────│
│ _id             │       │ _id             │
│ name            │◄──────│ institution_id  │
│ slug            │   1:N │ email           │
│ code            │       │ role            │
│ subscription    │       │ profile         │
│ settings        │       │ permissions     │
└────────┬────────┘       └─────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐       ┌─────────────────┐
│   OMRTemplate   │       │      Test       │
│─────────────────│       │─────────────────│
│ _id             │       │ _id             │
│ institution_id  │       │ institution_id  │
│ name            │◄──────│ template_id     │
│ type            │   1:N │ name            │
│ config          │       │ answer_key      │
│ calibration     │       │ config          │
└─────────────────┘       └────────┬────────┘
                                   │
                                   │ 1:N
                                   ▼
                          ┌─────────────────┐
                          │    OMRSheet     │
                          │─────────────────│
                          │ _id             │
                          │ test_id         │
                          │ student_id      │
                          │ images          │
                          │ processing      │
                          │ evaluation      │
                          └─────────────────┘
```

### Model Descriptions

| Model | Collection | Description |
|-------|------------|-------------|
| **Institution** | `institutions` | Organizations (schools, universities) with subscription and settings |
| **User** | `users` | User accounts with profiles, roles, and permissions |
| **OMRTemplate** | `omr_templates` | Sheet layout definitions with bubble positions |
| **Test** | `tests` | Exams with answer keys, marking schemes, and statistics |
| **OMRSheet** | `omr_sheets` | Individual answer sheets with processing and evaluation results |
| **UploadBatch** | `upload_batches` | Bulk upload tracking |

---

## API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login and get tokens | No |
| POST | `/auth/refresh` | Refresh access token | No |
| POST | `/auth/logout` | Logout user | Yes |
| GET | `/auth/me` | Get current user | Yes |
| POST | `/auth/forgot-password` | Request password reset | No |
| POST | `/auth/reset-password` | Reset password with token | No |
| POST | `/auth/verify-email` | Verify email address | No |
| PUT | `/auth/change-password` | Change password | Yes |

### User Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/users` | List users (paginated) | `read:users` |
| POST | `/users` | Create user | `create:users` |
| GET | `/users/stats` | Get user statistics | `view:analytics` |
| GET | `/users/{id}` | Get user by ID | `read:users` |
| PUT | `/users/{id}` | Update user | `update:users` |
| DELETE | `/users/{id}` | Delete user | `delete:users` |
| PUT | `/users/{id}/status` | Update user status | `update:users` |
| POST | `/users/bulk-import` | Bulk import from CSV | `bulk_import:users` |

### Institution Endpoints (Super Admin)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/institutions` | List all institutions |
| POST | `/admin/institutions` | Create institution |
| GET | `/admin/institutions/{id}` | Get institution |
| PUT | `/admin/institutions/{id}` | Update institution |
| DELETE | `/admin/institutions/{id}` | Delete institution |
| PUT | `/admin/institutions/{id}/status` | Update status |
| GET | `/admin/institutions/{id}/stats` | Get statistics |

### Template Endpoints (Coming Soon)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/templates` | List templates |
| POST | `/templates` | Create template |
| GET | `/templates/{id}` | Get template |
| PUT | `/templates/{id}` | Update template |
| POST | `/templates/{id}/calibrate` | Upload calibration image |

### Test Endpoints (Coming Soon)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tests` | List tests |
| POST | `/tests` | Create test |
| GET | `/tests/{id}` | Get test details |
| PUT | `/tests/{id}/answer-key` | Set answer key |
| POST | `/tests/{id}/publish` | Publish results |
| GET | `/tests/{id}/results` | Get all results |

### Sheet Endpoints (Coming Soon)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sheets/upload` | Upload single sheet |
| POST | `/sheets/upload/bulk` | Bulk upload |
| GET | `/sheets` | List sheets |
| GET | `/sheets/{id}` | Get sheet details |
| POST | `/sheets/{id}/process` | Process sheet |
| GET | `/sheets/needs-review` | Get flagged sheets |

---

## Authentication & Authorization

### JWT Token Flow

```
┌────────┐                              ┌────────┐
│ Client │                              │ Server │
└───┬────┘                              └───┬────┘
    │                                       │
    │  POST /auth/login                     │
    │  {email, password}                    │
    │──────────────────────────────────────►│
    │                                       │
    │  {access_token, refresh_token}        │
    │◄──────────────────────────────────────│
    │                                       │
    │  GET /users (Authorization: Bearer)   │
    │──────────────────────────────────────►│
    │                                       │
    │  200 OK (data)                        │
    │◄──────────────────────────────────────│
    │                                       │
    │  POST /auth/refresh                   │
    │  {refresh_token}                      │
    │──────────────────────────────────────►│
    │                                       │
    │  {new_access_token, new_refresh}      │
    │◄──────────────────────────────────────│
```

### User Roles

| Role | Description | Scope |
|------|-------------|-------|
| `super_admin` | Platform administrator | All institutions |
| `institution_admin` | Institution administrator | Own institution |
| `teacher` | Teaching staff | Own classes/tests |
| `student` | Student user | Own results |
| `parent` | Parent/guardian | Linked student results |

### Permissions

Permissions follow the format: `action:resource`

```python
# Examples
"create:users"        # Can create users
"read:tests"          # Can view tests
"upload:sheets"       # Can upload OMR sheets
"view:all_results"    # Can view all results
"view:own_results"    # Can view own results only
```

---

## OMR Processing Pipeline

### Processing Flow

```
┌──────────────┐
│ Image Upload │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 1. Image Loading & Validation        │
│    - Format check (PNG, JPG, PDF)    │
│    - Size validation                 │
│    - Corruption detection            │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 2. Preprocessing                     │
│    - Auto-orientation (portrait)     │
│    - Grayscale conversion            │
│    - Gaussian blur (noise reduction) │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 3. Sheet Detection                   │
│    - Canny edge detection            │
│    - Contour finding                 │
│    - 4-point boundary detection      │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 4. Perspective Transform             │
│    - Corner ordering                 │
│    - Perspective matrix calculation  │
│    - Warp transformation             │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 5. Bubble Detection                  │
│    - Otsu thresholding               │
│    - Contour detection               │
│    - Circularity filtering           │
│    - Grid sorting                    │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 6. Answer Extraction                 │
│    - Fill percentage calculation     │
│    - Threshold comparison            │
│    - BLANK/MULTIPLE detection        │
│    - Confidence scoring              │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 7. Evaluation                        │
│    - Answer key comparison           │
│    - Score calculation               │
│    - Negative marking                │
│    - Pass/fail determination         │
└──────┴───────────────────────────────┘
```

### Detection Results

Each detected answer includes:
- `question_number`: Question number
- `detected_mark`: A, B, C, D, BLANK, MULTIPLE, or INVALID
- `confidence`: 0.0 - 1.0 confidence score
- `fill_percentages`: Fill % for each option
- `flagged`: Whether manual review is needed

---

## Development

### Code Style

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint
flake8 app/
```

### Adding New Endpoints

1. Create router in `app/api/v1/{resource}/router.py`
2. Create schemas in `app/api/v1/{resource}/schemas.py`
3. Create service in `app/api/v1/{resource}/service.py`
4. Register router in `app/api/v1/router.py`

### Adding New Models

1. Create model in `app/models/{model}.py`
2. Export in `app/models/__init__.py`
3. Register in `app/main.py` Beanie initialization

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run with verbose output
pytest -v
```

---

## Deployment

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up MongoDB replica set
- [ ] Configure Redis persistence
- [ ] Set up S3/MinIO for file storage
- [ ] Configure SSL/TLS
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation
- [ ] Set up automated backups

### Docker Production

```bash
# Build production image
docker build -t omr-api:latest .

# Run with production settings
docker run -d \
  --name omr-api \
  -p 8000:8000 \
  -e DEBUG=false \
  -e SECRET_KEY=your-production-secret \
  -e MONGODB_URL=mongodb://mongo:27017 \
  omr-api:latest
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Support

For issues and feature requests, please use the GitHub issue tracker.
