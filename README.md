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
| `JWT_SECRET_KEY` | JWT signing secret (use 32+ characters) |
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

---

## Thunder Client — API Testing

Base URL: `http://127.0.0.1:5000`

**Auth header (for protected routes):**

| Header | Value |
| --- | --- |
| `Authorization` | `Bearer {{access_token}}` |
| `Content-Type` | `application/json` |

Copy `access_token` from the login response. In Thunder Client you can save it as an environment variable.

---

### Auth

#### POST `/api/auth/register` — Register a user (Public)

```json
{
  "full_name": "Thushi Demo",
  "email": "thushi@example.com",
  "password": "User123!",
  "date_of_birth": "1999-06-15",
  "language_preference": "tamil"
}
```

`language_preference` must be `tamil` or `english`. Role is always `user`.

**Success `201`**
```json
{
  "message": "User registered successfully.",
  "user": { "id": 3, "email": "thushi@example.com", "role": "user" },
  "health_profile": { "id": 2, "profile_id": 3 }
}
```

---

#### POST `/api/auth/login` — Login (Public)

```json
{
  "email": "user@penmozhi.com",
  "password": "User123!"
}
```

**Success `200`** — save `access_token` for later requests.

```json
{
  "message": "Login successful.",
  "access_token": "eyJ...",
  "user": { "id": 2, "email": "user@penmozhi.com", "role": "user" }
}
```

---

#### GET `/api/auth/profile` — Current user (Authenticated)

No body. Header: `Authorization: Bearer {{access_token}}`

**Success `200`**
```json
{
  "user": { "id": 2, "full_name": "Demo User", "role": "user" },
  "health_profile": { "id": 1, "profile_id": 2 }
}
```

---

#### POST `/api/auth/logout` — Logout (Authenticated)

No body required. Header: `Authorization: Bearer {{access_token}}`

**Success `200`**
```json
{ "message": "Logout successful." }
```

---

### Health Profiles

Replace `:id` with `health_profile.id` from profile / register.

#### GET `/api/health-profiles/:id` — Get own health profile (User / Owner)

No body. Auth required.

#### PUT `/api/health-profiles/:id` — Update health profile (User / Owner)

```json
{
  "weight": 62.5,
  "height": 165,
  "nutritional_needs": "Balanced meals with iron-rich foods",
  "health_risks": "none noted"
}
```

`height` in cm (or meters if ≤ 3). BMI is calculated automatically.

#### GET `/api/health-profiles/:id/risks` — Risk summary (User / Owner)

No body. Returns BMI-based risk notes plus stored `health_risks`.

---

### Cycle History

#### POST `/api/cycles` — Log a cycle (User)

```json
{
  "cycle_start_date": "2026-04-01",
  "cycle_end_date": "2026-04-05",
  "flow_intensity": "medium"
}
```

Log a second cycle with a later start date to see prediction update:

```json
{
  "cycle_start_date": "2026-04-29",
  "cycle_end_date": "2026-05-03",
  "flow_intensity": "heavy"
}
```

#### GET `/api/cycles/my` — Own cycle history (User / Owner)

No body.

#### GET `/api/cycles/predict-next` — Next-period prediction (User / Owner)

No body.

**Success `200`**
```json
{
  "predicted_next_period_date": "2026-05-27",
  "based_on_cycles": 2,
  "latest_cycle": { "id": 2, "cycle_start_date": "2026-04-29" }
}
```

---

### Symptom Tracking

#### POST `/api/symptoms` — Log a symptom (User)

```json
{
  "category": "cramps",
  "pain_severity": 8,
  "mood_status": "irritable",
  "sleep_metrics": "6h",
  "date_time": "2026-05-02T10:30:00"
}
```

`pain_severity` is 0–10. Severity ≥ 7 returns an `ai_flag` in the response.

#### GET `/api/symptoms/my` — Own symptoms (User / Owner)

No body.

#### GET `/api/symptoms/trends` — Pain / category trends (User / Owner)

No body.

---

### Medication / Supplement Reminders

#### POST `/api/reminders` — Create reminder (User)

```json
{
  "item_name": "Iron tablet",
  "reminder_type": "medication",
  "scheduled_time": "08:00:00",
  "dosage": "1 tablet"
}
```

#### GET `/api/reminders/my` — Own reminders (User / Owner)

No body.

#### PUT `/api/reminders/:id` — Update reminder (User / Owner)

```json
{
  "dosage": "1 tablet with food",
  "scheduled_time": "08:30:00"
}
```

#### POST `/api/reminders/:id/mark-taken` — Mark taken (User / Owner)

No body (empty JSON `{}` is fine).

#### POST `/api/reminders/:id/snooze` — Snooze (User / Owner)

```json
{
  "minutes": 10
}
```

#### DELETE `/api/reminders/:id` — Delete reminder (User / Owner)

No body.

---

### AI Health Assistant

#### POST `/api/ai-assistant/chat` — Chat (User)

```json
{
  "message": "I have severe pain and irregular cycles. Could this be related to PCOS?"
}
```

#### GET `/api/ai-assistant/recommendations` — Recommendations (User / Owner)

No body.

#### GET `/api/ai-assistant/sessions` — Saved chat sessions (User / Owner)

No body.

---

### PCOS Disorder Status

#### GET `/api/pcos-status/my` — Own PCOS statuses (User / Owner)

No body. Use an `id` from `pcos_statuses` for update/history.

#### PUT `/api/pcos-status/:id` — Update status (User Owner / Admin)

```json
{
  "disorder_type": "PCOS",
  "diagnosis_status": "suspected",
  "diagnosed_date": "2026-05-01"
}
```

Creates a new history row; response returns the updated (latest) status.

#### GET `/api/pcos-status/:id/history` — Status history (User / Owner)

No body.

---

### Educational Resources

#### GET `/api/education` — List resources (Public)

Optional query: `?category=pcos` (or `cycle`, `nutrition`, …)

No body. No auth required.

#### GET `/api/education/:id` — Resource detail (Public)

No body. No auth required.

#### POST `/api/education` — Create resource (Admin)

Login as `admin@penmozhi.com` first.

```json
{
  "article_title": "Hydration Tips for Cycle Health",
  "content_category": "nutrition",
  "content_body": "Drink water regularly throughout the day to support energy and mood.",
  "publication_date": "2026-06-01"
}
```

#### PUT `/api/education/:id` — Update resource (Admin)

```json
{
  "article_title": "Hydration Tips — Updated",
  "content_category": "nutrition"
}
```

#### DELETE `/api/education/:id` — Delete resource (Admin)

No body.

---

### Forum

All forum routes require authentication. Posts/comments display as **Anonymous**.

#### GET `/api/forum` — List posts (Authenticated)

No body.

#### GET `/api/forum/:id` — Post detail + comments (Authenticated)

No body.

#### POST `/api/forum` — Create post (User)

```json
{
  "title": "Tips for tracking cycles",
  "body": "Logging two full cycles helped my next-period prediction update.",
  "content_id": 1
}
```

`content_id` is optional (FK to an educational resource).

#### PUT `/api/forum/:id` — Update own post (User / Owner)

```json
{
  "body": "Updated: logging two full cycles made the prediction clearer."
}
```

#### POST `/api/forum/:id/comments` — Add comment (User)

```json
{
  "body": "Thanks, this helped me start logging!"
}
```

#### DELETE `/api/forum/:id` — Delete post (User Owner / Admin)

No body.

---

## Suggested Thunder Client test order (viva)

1. `POST /api/auth/login` as `user@penmozhi.com` → copy token  
2. `POST /api/cycles` twice (two start dates) → `GET /api/cycles/predict-next`  
3. `POST /api/symptoms` with `pain_severity: 8` → note `ai_flag`  
4. `POST /api/ai-assistant/chat` about pain/PCOS  
5. `GET /api/pcos-status/my` → `PUT /api/pcos-status/:id`  
6. Login as admin → `POST /api/education` → view on `GET /api/education`
