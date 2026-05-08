# SynapHR AI - AI-Powered Human Resource Management System

A comprehensive, production-ready HRMS with an integrated AI chatbot and intelligent automation engine.

## 🚀 Features

### Core HRMS
- **Employee Management**: Complete employee lifecycle management
- **Department & Designation**: Hierarchical organizational structure
- **Attendance Tracking**: Check-in/out, geo-fencing, overtime calculation
- **Leave Management**: Leave types, allocations, requests with approval workflow
- **Payroll Management**: Salary structures, monthly payroll processing
- **Performance Reviews**: Goal setting, performance evaluations
- **Notifications**: Real-time notifications via WebSocket

### AI Automation System
- **Rule-Based Engine**: Configurable automation rules triggered by HRMS events (employee created, leave approved, attendance marked, payroll processed, etc.)
- **Condition Evaluation**: JSON-based condition expressions to filter when actions should execute
- **Action Types**: Send notifications, update record fields, create records, or trigger webhooks
- **Priority Ordering**: Rules execute in priority order for fine-grained control
- **Event-Driven**: Automatically evaluated via Django signals on all major HRMS events

### AI Chatbot
- **DeepSeek Integration**: OpenAI-compatible API for chat completions
- **Semantic Search**: Search over company documents and policies
- **Document Ingestion**: Upload and embed HR documents for AI context
- **Conversation History**: Persistent chat history per user
- **Streaming Responses**: Real-time token-by-token streaming via WebSocket

### Security
- **JWT Authentication**: Access + Refresh token pair
- **Brute Force Protection**: django-axes integration
- **Role-Based Access**: Admin, HR, Manager, Employee roles
- **Rate Limiting**: Per-user and anonymous throttling

## 🎥 Demo

![SynapHR AI Demo](video.mp4)

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| Django 5.1 | Web framework |
| Django REST Framework | REST API |
| PostgreSQL 16 + pgvector | Database + vector embeddings |
| Redis 7 | Cache, sessions, Celery broker, Channels layer |
| Celery | Async task queue |
| Django Channels | WebSocket support |
| SimpleJWT | JWT authentication |
| drf-spectacular | OpenAPI/Swagger docs |
| DeepSeek API | AI chat completions & embeddings |

### Frontend
- React 18 + TypeScript
- Tailwind CSS + shadcn/ui
- Zustand state management
- React Router v6
- Recharts for data visualization

## 📋 Prerequisites

### Docker Setup (Recommended)
- Docker & Docker Compose

### Venv Setup (Lightweight, no Docker)
- Python 3.12+

## 🔧 Installation & Setup

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd SynapHR-AI

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Build and start all services
docker-compose up --build -d

# Run migrations
docker-compose exec web python manage.py migrate

# Seed default data (optional - creates demo admin user, departments, etc.)
docker-compose exec web python manage.py seed_data

# Access the application
# API: http://localhost:8000
# Admin Panel: http://localhost:8000/admin/
# Swagger Docs: http://localhost:8000/api/docs/swagger/
```

#### Default Admin Credentials

| Field    | Value                |
|----------|----------------------|
| Email    | admin@synaphr.ai     |
| Password | admin@123            |

> **Note**: These credentials are created automatically when you run the `seed_data` management command. Change the password immediately in production.

### Option 2: Virtual Environment (venv) - No Docker Required

This mode uses **SQLite** instead of PostgreSQL and **in-memory** backends instead of Redis. No external services needed.

#### Windows Quick Setup

```batch
:: 1. Create virtual environment
python -m venv venv

:: 2. Activate virtual environment
venv\Scripts\activate

:: 3. Install dependencies
pip install -r requirements-venv.txt

:: 4. Copy the venv environment file
copy .env.venv .env

:: 5. Run migrations
set DJANGO_SETTINGS_MODULE=config.settings_venv
python manage.py migrate

:: 6. Seed default data (optional)
python manage.py seed_data

:: 7. Start development server
python manage.py runserver 0.0.0.0:8000
```

#### Manual Setup (All Platforms)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (Linux/Mac)
source venv/bin/activate

# Install dependencies (lighter venv-specific requirements)
pip install -r requirements-venv.txt

# Copy venv environment file
# Windows:
copy .env.venv .env
# Linux/Mac:
cp .env.venv .env

# Run migrations (using venv settings)
set DJANGO_SETTINGS_MODULE=config.settings_venv    # Windows
export DJANGO_SETTINGS_MODULE=config.settings_venv  # Linux/Mac
python manage.py migrate

# Seed default data (optional)
python manage.py seed_data

# Start development server
python manage.py runserver 0.0.0.0:8000
```

The server will start at **http://localhost:8000**.

> **Note**: In venv mode, Celery tasks run synchronously (eager mode), so no separate Celery worker is needed. Scheduled tasks (payroll, reminders, etc.) won't run automatically - they can be triggered manually via management commands.

#### What's Different in Venv Mode?

| Service | Docker Mode | Venv Mode |
|---------|-------------|-----------|
| Database | PostgreSQL 16 + pgvector | SQLite |
| Cache | Redis | Local memory |
| Channel Layer | Redis | In-memory |
| Celery Broker | Redis | Memory (eager) |
| Celery Worker | Separate process | Same process (synchronous) |
| Email | SMTP | Console (printed to terminal) |
| Static Files | WhiteNoise compressed | Django staticfiles |

## 🐳 Docker Update

To update the project to the latest version using Docker:

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose up --build -d

# Run any new migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput --clear
```

### Docker Commands Reference

```bash
# View logs
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f web

# Access the web container shell
docker-compose exec web bash

# Restart a specific service
docker-compose restart web

# Stop all services
docker-compose down

# Stop all services and remove volumes (WARNING: deletes database data)
docker-compose down -v
```

## 📚 API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/api/docs/swagger/
- **ReDoc**: http://localhost:8000/api/docs/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### API Endpoints Overview

#### Authentication (`/api/v1/auth/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/token/` | Get JWT tokens |
| POST | `/token/refresh/` | Refresh access token |
| POST | `/token/verify/` | Verify token validity |
| POST | `/register/` | Register new user |
| POST | `/login/` | Login with credentials |
| GET | `/me/` | Get current user profile |
| PUT | `/change-password/` | Change password |

#### HRMS Core (`/api/v1/hr/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/` | Dashboard statistics |
| CRUD | `/departments/` | Department management |
| CRUD | `/designations/` | Designation management |
| CRUD | `/employees/` | Employee management |
| CRUD | `/attendance/` | Attendance records |
| CRUD | `/leave-types/` | Leave type configuration |
| CRUD | `/leave-allocations/` | Leave balance management |
| CRUD | `/leave-requests/` | Leave request workflow |
| POST | `/leave-requests/{id}/approve/` | Approve leave |
| POST | `/leave-requests/{id}/reject/` | Reject leave |
| CRUD | `/holidays/` | Holiday calendar |
| CRUD | `/salary-structures/` | Salary configuration |
| CRUD | `/payroll/` | Payroll management |
| POST | `/payroll/process/` | Process monthly payroll |
| CRUD | `/performance-reviews/` | Performance reviews |
| CRUD | `/goals/` | Goal management |
| GET | `/notifications/` | User notifications |
| CRUD | `/automation-rules/` | Automation rule management |
| GET | `/reports/attendance/` | Attendance reports |
| GET | `/reports/payroll/` | Payroll reports |

#### AI Chatbot (`/api/v1/chatbot/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | AI service health check |
| CRUD | `/conversations/` | Chat conversations |
| GET | `/conversations/{id}/messages/` | Chat history |
| POST | `/chat/` | Send message to AI |
| CRUD | `/documents/` | Document management |
| POST | `/documents/ingest/` | Ingest document for AI context |
| POST | `/documents/search/` | Semantic search |
| POST | `/feedback/` | Rate AI response |

## 🔐 Environment Variables

See [`.env.example`](.env.example) for all configuration options.

Key variables:
```
DJANGO_SECRET_KEY=your-secret-key
DB_NAME=synaphr_ai
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
DEEPSEEK_API_KEY=your-deepseek-api-key
```

### Venv Mode
See [`.env.venv`](.env.venv) for venv-specific configuration.

Key variables:
```
DJANGO_SECRET_KEY=django-insecure-venv-dev-key-...
DJANGO_DEBUG=True
DEEPSEEK_API_KEY=your-deepseek-api-key   # Optional - leave empty to disable AI
```

In venv mode, only `DJANGO_SECRET_KEY` and `DEEPSEEK_API_KEY` are relevant. Database, Redis, and email settings are pre-configured for local development.

## 🏗 Project Structure

```
SynapHR-AI/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Docker/Production settings
│   ├── settings_venv.py         # Venv/Local development settings
│   ├── urls.py                  # Main URL configuration
│   ├── wsgi.py                  # WSGI application
│   ├── asgi.py                  # ASGI application (Channels)
│   ├── celery.py                # Celery configuration
│   ├── pagination.py            # Custom pagination classes
│   ├── exceptions.py            # Custom exception handler
│   └── apps/
│       ├── accounts/            # User authentication app
│       │   ├── models.py        # Custom User model
│       │   ├── serializers.py
│       │   ├── views.py         # Auth views (register, login, etc.)
│       │   ├── urls.py
│       │   ├── admin.py
│       │   └── tasks.py         # Celery tasks
│       ├── hrms/                # Core HRMS app
│       │   ├── models.py        # All HRMS models (incl. AutomationRule)
│       │   ├── serializers.py
│       │   ├── views.py         # All HRMS API views
│       │   ├── urls.py
│       │   ├── admin.py
│       │   ├── signals.py       # Notification + automation signals
│       │   ├── automation.py    # Rule engine for AI automation
│       │   └── tasks.py         # Celery tasks
│       ├── chatbot/             # AI Chatbot app
│       │   ├── models.py        # Chat models
│       │   ├── serializers.py
│       │   ├── views.py         # Chat API views
│       │   ├── urls.py
│       │   ├── admin.py
│       │   ├── services.py      # DeepSeek AI integration
│       │   ├── routing.py       # WebSocket routing
│       │   └── tasks.py         # Embedding sync tasks
│       └── notifications/       # Real-time notifications
│           ├── consumers.py     # WebSocket consumers
│           ├── routing.py
│           ├── views.py
│           └── urls.py
├── apps/                       # Legacy apps (moved to config/apps/)
├── manage.py
├── requirements.txt             # Full requirements (Docker mode)
├── requirements-venv.txt        # Lighter requirements (venv mode)
├── .env.example                 # Docker mode env template
├── .env.venv                    # Venv mode env template
├── Dockerfile
├── docker-compose.yml
├── static/
├── media/
├── logs/
└── README.md
```

## 🧪 Testing

```bash
# Run all tests (venv mode)
set DJANGO_SETTINGS_MODULE=config.settings_venv   # Windows
export DJANGO_SETTINGS_MODULE=config.settings_venv # Linux/Mac
python manage.py test

# Run tests with coverage
pytest --cov=config --cov-report=html
```

## 📦 Deployment

### Production Checklist
1. Set `DJANGO_DEBUG=False`
2. Generate a strong `DJANGO_SECRET_KEY`
3. Configure proper `ALLOWED_HOSTS`
4. Set up HTTPS with a reverse proxy (Nginx)
5. Configure email settings
6. Set up database backups
7. Configure monitoring and logging

### Docker Production Deployment
```bash
# Build and start services
docker-compose -f docker-compose.yml up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```


## 📄 License

MIT License - see LICENSE file for details.
