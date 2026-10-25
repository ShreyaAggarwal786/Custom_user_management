# DRF Assignment: User & Client Management API

A Django REST Framework project with JWT login, user management, client management and an OTP system (email verification and password reset) with rate limiting.

## Tech Stack

- Python 3.13
- Django 6.1.2
- Django REST Framework
- djangorestframework-simplejwt (JWT authentication)
- SQLite (default database)
- Pillow (profile images)

## Features

- User registration, listing, update and soft delete (status becomes `inactive`)
- Login with email and password, returns JWT access and refresh tokens
- Send OTP and verify OTP (email verification)
- Forgot password and reset password using OTP
- Client CRUD (login required) with `created_by` and `modified_by` tracking
- Pagination on list APIs
- All required-field validations are handled in the serializers, not in the models

## OTP Rate Limit (Send OTP)

- A user can request an OTP only **3 times in 12 hours** on the Send OTP API.
- After the limit is crossed, further requests are blocked for **12 hours**.
- The API returns a `400` error with the message and the time when the user can try again:

```json
{
    "detail": "You have exceeded the maximum number of OTP requests. Please try again after 12 hours. You can request a new OTP after 26 Oct 2026, 12:41 PM."
}
```

- If the email fails to send, the request is **not** counted.
- The limit applies only to Send OTP. Forgot Password has no limit.

## Project Structure

```
DRF_Assignment/
├── config/                 # Project settings and main urls
├── UserModel/              # Main app
│   ├── models.py           # User and Client models
│   ├── serializers.py      # Serializers and validations
│   ├── views.py            # API views
│   ├── urls.py             # App routes
│   ├── utils.py            # OTP generate, send, verify and rate limit
│   ├── admin.py
│   └── migrations/
├── manage.py
├── requirements.txt
└── README.md
```

## Setup (Windows)

1. Clone the repository

```
git clone https://github.com/ShreyaAggarwal786/Custom_user_management.git
cd YOUR_REPO_NAME
```

2. Create and activate a virtual environment

```
python -m venv django_venv
django_venv\Scripts\activate
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Set email credentials (PowerShell, same terminal where the server will run)

```
$env:EMAIL_HOST_USER="your-email@gmail.com"
$env:EMAIL_HOST_PASSWORD="your-gmail-app-password"
```

For Gmail, use an App Password (2-Step Verification must be ON). For local testing without real emails, set this in `settings.py` and the OTP will print in the terminal:

```
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

5. Run migrations

```
python manage.py makemigrations UserModel
python manage.py migrate
```

6. Create a superuser (optional)

```
python manage.py createsuperuser
```

7. Start the server

```
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/`.

## Settings Used

| Setting | Purpose |
|---|---|
| `OTP_EXPIRY_MINUTES` | How long an OTP stays valid |
| `OTP_MAX_ATTEMPTS` | Maximum wrong OTP attempts |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Email credentials (environment variables) |
| `TIME_ZONE` | Timezone used in the "try again after" time (for example `Asia/Kolkata`) |

## API Endpoints

Base URL: `http://127.0.0.1:8000/api/`

### Users

| Method | Endpoint | Description |
|---|---|---|
| GET | `/users/` | List users (paginated) |
| POST | `/users/` | Register a user |
| GET | `/users/<id>/` | Get one user |
| PUT / PATCH | `/users/<id>/` | Update a user |
| DELETE | `/users/<id>/` | Deactivate a user (soft delete) |

### Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login/` | Login, returns access and refresh tokens |
| POST | `/auth/token/refresh/` | Get a new access token |
| POST | `/auth/send-otp/` | Send verification OTP (rate limited) |
| POST | `/auth/verify-otp/` | Verify the OTP |
| POST | `/auth/forgot-password/` | Send password reset OTP |
| POST | `/auth/reset-password/` | Reset password using OTP |

### Clients (requires `Authorization: Bearer <access_token>`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/client/` | List clients (paginated) |
| POST | `/client/` | Create a client |
| GET | `/client/<id>/` | Get one client |
| PUT / PATCH | `/client/<id>/` | Update a client |
| DELETE | `/client/<id>/` | Deactivate a client (soft delete) |

Pagination supports `?page=2&page_size=5`.

## Sample Requests

Register a user (`POST /api/users/`):

```json
{
    "username": "john",
    "email": "john@example.com",
    "password": "StrongPass@123",
    "confirm_password": "StrongPass@123"
}
```

Login (`POST /api/auth/login/`):

```json
{
    "email": "john@example.com",
    "password": "StrongPass@123"
}
```

Send OTP (`POST /api/auth/send-otp/`):

```json
{
    "email": "shreya@example.com"
}
```

Create a client (`POST /api/client/`):

```json
{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "contact_number": "9876543210",
    "address": "Some street, Some city",
    "country": "India"
}
```

## Validation Rules

- **User create:** `username`, `email`, `password` and `confirm_password` are required. Passwords must match and pass Django's password validators. Email and username must be unique.
- **User update:** `username` and `email` cannot be empty if sent. `profiles` cannot be changed through the API.
- **Client:** `first_name`, `last_name`, `email`, `contact_number`, `address` and `country` are required. Email must be unique.
- All other model fields use `null=True` and `blank=True`.

