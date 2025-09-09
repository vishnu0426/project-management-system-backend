# Agno WorkSphere Backend API

A comprehensive project management platform backend built with FastAPI, PostgreSQL, and modern Python technologies.

## Features

- **Authentication & Authorization**: JWT-based auth with 2FA support
- **User Management**: Profile management, avatar upload, notification preferences
- **Organization Management**: Multi-tenant organization support with role-based access
- **Project & Kanban Management**: Full project lifecycle with kanban boards
- **Team Management**: Member invitations, role assignments, activity tracking
- **File Upload**: Secure file handling for avatars, logos, and attachments
- **Real-time Features**: WebSocket support for live collaboration
- **Security**: Comprehensive security measures and input validation

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy (async)
- **Authentication**: JWT with bcrypt password hashing
- **File Storage**: Local storage with S3 support
- **Real-time**: WebSockets
- **Validation**: Pydantic schemas
- **Migrations**: Alembic

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis (optional, for caching)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up database:
```bash
# Create database
createdb agno_worksphere

# Run migrations
alembic upgrade head
```

6. Start the development server:
```bash
python run.py
```

The API will be available at `http://localhost:3001`

## API Documentation

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:3001/docs`
- **ReDoc**: `http://localhost:3001/redoc`

## Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agno_worksphere

# Authentication
JWT_SECRET=your-super-secret-jwt-key
JWT_EXPIRES_IN=15

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# File Storage
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=agno-worksphere-uploads
```

## Development

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

### Code Quality

Format code:
```bash
black app/
isort app/
```

Lint code:
```bash
flake8 app/
```

### Testing

Run tests:
```bash
pytest
```

With coverage:
```bash
pytest --cov=app
```

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/     # API endpoints
│   │       └── router.py      # Main router
│   ├── core/
│   │   ├── database.py        # Database configuration
│   │   ├── security.py        # Security utilities
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── deps.py           # Dependencies
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── config.py            # Configuration
│   └── main.py              # FastAPI app
├── alembic/                 # Database migrations
├── requirements.txt         # Dependencies
├── .env.example            # Environment template
└── run.py                  # Development server
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh-token` - Refresh access token
- `POST /api/v1/auth/logout` - User logout

### Users
- `GET /api/v1/users/profile` - Get user profile
- `PUT /api/v1/users/profile` - Update user profile
- `POST /api/v1/users/avatar` - Upload avatar

### Organizations
- `GET /api/v1/organizations` - List organizations
- `POST /api/v1/organizations` - Create organization
- `GET /api/v1/organizations/{id}` - Get organization
- `PUT /api/v1/organizations/{id}` - Update organization

### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project

### Boards & Cards
- `GET /api/v1/projects/{id}/boards` - Get project boards
- `POST /api/v1/projects/{id}/boards` - Create board
- `GET /api/v1/boards/{id}/columns` - Get board columns
- `GET /api/v1/columns/{id}/cards` - Get column cards
- `POST /api/v1/columns/{id}/cards` - Create card

## Security

The API implements several security measures:
- JWT token authentication
- Password hashing with bcrypt
- Rate limiting
- Input validation
- SQL injection prevention
- XSS protection
- CORS configuration

## Deployment

### Docker

Build and run with Docker:
```bash
docker build -t agno-worksphere-api .
docker run -p 3001:3001 agno-worksphere-api
```

### Production

For production deployment:
1. Set `DEBUG=False` in environment
2. Use a production WSGI server (gunicorn)
3. Set up proper database connection pooling
4. Configure reverse proxy (nginx)
5. Set up SSL/TLS certificates
6. Configure monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run code quality checks
6. Submit a pull request

## License

This project is licensed under the MIT License.
