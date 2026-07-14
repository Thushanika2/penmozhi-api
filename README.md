# Penmozhi Women's Health API

Flask REST API with MySQL for menstrual cycle tracking, symptom logging, medication reminders, PCOS status, educational resources, and community forum.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and update values.

Create the database:

```bash
mysql -u root -p -e "CREATE DATABASE penmozhi_db;"
```

Run the API (tables are created automatically):

```bash
python run.py
```

Base URL: `http://127.0.0.1:5000`

## Environment Variables

| Variable | Description |
| --- | --- |
| `DB_USER` | MySQL username |
| `DB_PASSWORD` | MySQL password |
| `DB_HOST` | MySQL host |
| `DB_PORT` | MySQL port (default 3306) |
| `DB_NAME` | Database name |
| `JWT_SECRET_KEY` | JWT signing secret |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` | Token expiry in minutes |
| `FLASK_DEBUG` | Enable Flask debug mode |

## Seed the database

```bash
python run_seeders.py
```

### Seeded accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@penmozhi.com` | `Admin123!` |
| User | `user@penmozhi.com` | `User123!` |

Admin accounts can only be created via seeders — public registration creates `user` role only, and auto-creates an empty HealthProfile (+ default PCOS status).

## Key Endpoints

### Auth
- `POST /api/auth/register` — register user (+ empty health profile)
- `POST /api/auth/login` — login and receive JWT
- `POST /api/auth/logout` — logout (client-side token discard)
- `GET /api/auth/profile` — current user + health profile

### Health & PCOS
- `GET/PUT /api/health-profiles/:id` — owner health profile
- `GET /api/health-profiles/:id/risks` — BMI / risk summary
- `GET /api/pcos-status/my` — own PCOS statuses
- `PUT /api/pcos-status/:id` — update status (user owner / admin)
- `GET /api/pcos-status/:id/history` — status history

### Cycle & Symptoms
- `POST /api/cycles` — log a cycle
- `GET /api/cycles/my` — own cycle history
- `GET /api/cycles/predict-next` — next-period prediction
- `POST /api/symptoms` — log a symptom
- `GET /api/symptoms/my` — own symptoms
- `GET /api/symptoms/trends` — pain/category trends

### Reminders & AI
- `POST /api/reminders` · `GET /api/reminders/my`
- `PUT/DELETE /api/reminders/:id`
- `POST /api/reminders/:id/mark-taken` · `POST /api/reminders/:id/snooze`
- `POST /api/ai-assistant/chat`
- `GET /api/ai-assistant/recommendations` · `GET /api/ai-assistant/sessions`

### Education & Forum
- `GET /api/education` — public list (`?category=`)
- `GET /api/education/:id` — public detail
- `POST/PUT/DELETE /api/education` — admin content management
- `GET/POST /api/forum` · `GET/PUT/DELETE /api/forum/:id`
- `POST /api/forum/:id/comments`
