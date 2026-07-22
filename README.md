# Penmozhi Women's Health API

Penmozhi is a Flask REST API for women’s health tracking. It covers authentication, health profiles, cycle logging, symptom tracking, reminders, PCOS status, educational resources, AI support, and a community forum.

This README is written for testing the API in Postman with the same routes and request formats implemented in the backend.

---

## 1. Local setup

### Requirements

- Python 3.10+
- MySQL Server
- Postman

### Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root:

```env
DB_USER=your_user_name
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=penmozhi_db
JWT_SECRET_KEY=change-this-to-a-long-secret-key
JWT_ACCESS_TOKEN_EXPIRES_MINUTES=1440
FLASK_DEBUG=True
```

### Create the database

```bash
mysql -u root -p -e "CREATE DATABASE penmozhi_db;"
```

### Start the server

```bash
python run.py
```

Base URL:

```text
http://127.0.0.1:5000
```

---

## 2. Seed demo data

Run the seeders to create sample users, health data, reminders, education resources, forum content, and AI sessions:

```bash
python run_seeders.py
```

### Demo accounts

| Role | Email               | Password   |
| ---- | ------------------- | ---------- |
| User | `user@penmozhi.com` | `User123!` |

The seeded data also creates:

- a health profile for the demo user
- cycle logs
- symptom logs
- reminders
- educational resources
- a forum post and comment
- AI assistant session data

---

## 3. Postman setup

Create a new Postman collection called `Penmozhi API`.

Create a new environment called `Penmozhi Local` with these variables:

| Variable       | Value                   |
| -------------- | ----------------------- |
| `base_url`     | `http://127.0.0.1:5000` |
| `access_token` | empty                   |

### Important Postman notes

- Use `raw JSON` for request bodies.
- For protected routes, add this header:

```text
Authorization: Bearer {{access_token}}
```

- For all examples below, use `http://127.0.0.1:5000` in the URL instead of typing the full host each time.

---

## 4. Authentication routes

### Register a user

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/auth/register
```

Body:

```json
{
  "full_name": "Thushi Demo",
  "email": "thushi@example.com",
  "password": "User123!",
  "date_of_birth": "1999-06-15",
  "language_preference": "tamil"
}
```

### Login

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/auth/login
```

Body:

```json
{
  "email": "user@penmozhi.com",
  "password": "User123!"
}
```

Save the returned `access_token` in the Postman `access_token` variable.

### Get current profile

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/auth/profile
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Update current profile language

Method: `PATCH`

URL:

```text
http://127.0.0.1:5000/api/auth/profile
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "language_preference": "english"
}
```

### Logout

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/auth/logout
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 5. Health profile routes

Use the health profile id returned by the register/login/profile response for the detail routes below.

### Get one health profile

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/health-profiles/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Update one health profile

Method: `PUT`

URL:

```text
http://127.0.0.1:5000/api/health-profiles/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "weight": 62.5,
  "height": 1.63,
  "nutritional_needs": "Balanced meals with iron-rich foods",
  "health_risks": "Occasional fatigue"
}
```

### Get health profile risk summary

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/health-profiles/1/risks
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 6. Cycle routes

### Create a cycle entry

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/cycles
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "cycle_start_date": "2026-04-01",
  "cycle_end_date": "2026-04-05",
  "flow_intensity": "medium"
}
```

### Get my cycle history

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/cycles/my
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Predict the next period

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/cycles/predict-next
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 7. Symptom routes

### Create a symptom entry

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/symptoms
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "category": "cramps",
  "pain_severity": 8,
  "mood_status": "irritable",
  "sleep_metrics": "6h",
  "date_time": "2026-05-02T10:30:00"
}
```

### Get my symptoms

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/symptoms/my
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Get symptom trends

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/symptoms/trends
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 8. Reminder routes

### Create a reminder

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/reminders
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "item_name": "Iron tablet",
  "reminder_type": "medication",
  "scheduled_time": "08:00:00",
  "dosage": "1 tablet"
}
```

### Get my reminders

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/reminders/my
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Update a reminder

Method: `PUT`

URL:

```text
http://127.0.0.1:5000/api/reminders/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "dosage": "1 tablet with food",
  "scheduled_time": "08:30:00"
}
```

### Mark reminder as taken

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/reminders/1/mark-taken
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Snooze a reminder

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/reminders/1/snooze
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "minutes": 10
}
```

### Delete a reminder

Method: `DELETE`

URL:

```text
http://127.0.0.1:5000/api/reminders/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 9. AI assistant routes

### Chat with the assistant

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/ai-assistant/chat
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "message": "I have severe pain and irregular cycles. Could this be related to PCOS?"
}
```

### Get recommendations

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/ai-assistant/recommendations
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Get assistant sessions

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/ai-assistant/sessions
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 10. PCOS status routes

### Get my PCOS status

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/pcos-status/my
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Update PCOS status

Method: `PUT`

URL:

```text
http://127.0.0.1:5000/api/pcos-status/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "disorder_type": "PCOS",
  "diagnosis_status": "suspected",
  "diagnosed_date": "2026-05-01"
}
```

### Get PCOS status history

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/pcos-status/1/history
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 11. Education routes

### List education resources

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/education
```

### Filter by category

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/education?category=pcos
```

### Get one resource

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/education/1
```

### Create a resource (admin only)

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/education
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "article_title": "Hydration Tips for Cycle Health",
  "content_category": "nutrition",
  "content_body": "Drink water regularly throughout the day to support energy and mood.",
  "publication_date": "2026-06-01"
}
```

### Update a resource (admin only)

Method: `PUT`

URL:

```text
http://127.0.0.1:5000/api/education/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "article_title": "Hydration Tips — Updated",
  "content_category": "nutrition"
}
```

### Delete a resource (admin only)

Method: `DELETE`

URL:

```text
http://127.0.0.1:5000/api/education/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 12. Forum routes

### List forum posts

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/forum
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Get one forum post with comments

Method: `GET`

URL:

```text
http://127.0.0.1:5000/api/forum/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

### Create a forum post

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/forum
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "title": "Tips for tracking cycles",
  "body": "Logging my symptoms helped me understand my cycle better.",
  "content_id": 1
}
```

### Update your own post

Method: `PUT`

URL:

```text
http://127.0.0.1:5000/api/forum/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "body": "Updated: logging symptoms helped me understand my cycle better."
}
```

### Add a comment

Method: `POST`

URL:

```text
http://127.0.0.1:5000/api/forum/1/comments
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

Body:

```json
{
  "body": "Thanks, this helped me start logging!"
}
```

### Delete a forum post

Method: `DELETE`

URL:

```text
http://127.0.0.1:5000/api/forum/1
```

Headers:

```text
Authorization: Bearer {{access_token}}
```

---

## 13. Recommended Postman test order

1. Register a user or use a seeded account.
2. Login and save the returned token.
3. View your profile.
4. Update your health profile.
5. Create a cycle entry.
6. Create a symptom entry.
7. Create a reminder.
8. Ask the AI assistant for recommendations.
9. View your PCOS status.
10. Browse education resources.
11. Create a forum post.
12. Add a comment.

---

## 14. Troubleshooting

- `401` or `403` means the token is missing, invalid, or expired.
- `400` usually means the request body or data format is incorrect.
- `404` means the requested resource or id was not found.
- `500` usually indicates a server or database issue.
- Make sure MySQL is running and your `.env` values are correct.
- If the server does not start, verify that dependencies were installed successfully.
