# Custom User Management & Authentication API

Django REST Framework project with a custom User model (AbstractUser), user CRUD
with soft delete, JWT login, OTP verification, and forgot/reset password.

## Features
- Custom `User` model with profile, status, and emergency contact fields
- User CRUD at `/api/users/` (DELETE is a soft delete: status -> inactive)
- Welcome email on user creation
- JWT login with email + password
- OTP send/verify (5-minute expiry, single use, max 5 attempts)
- Forgot/reset password via OTP
- Passwords are hashed; passwords and OTP codes are never returned

## Tech Stack
Python 3.13, Django, Django REST Framework, SimpleJWT, Pillow, python-dotenv, SQLite

## Setup (Windows)
1. Clone and enter the folder:
```
   git clone https://github.com/ShreyaAggarwal786/Custom_user_management.git
   cd Custom_user_management
```
2. Create and activate a virtual environment:
```
   python -m venv django_venv
   django_venv\Scripts\activate
```
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your values.
5. Run migrations:
```
   python manage.py makemigrations
   python manage.py migrate
```
6. (Optional) `python manage.py createsuperuser`
7. Start the server: `python manage.py runserver`

## Email Configuration
Emails go through Gmail SMTP. Set in `.env`:
```
EMAIL_HOST_USER=your_address@gmail.com
EMAIL_HOST_PASSWORD=your_16_char_app_password
```
A Gmail App Password is required (enable 2-Step Verification first).
For local testing without real email, set `EMAIL_BACKEND` in settings.py to
`django.core.mail.backends.console.EmailBackend`.

## API Endpoints
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /api/users/ | No | Create user, send welcome email |
| GET | /api/users/ | Yes | List users |
| GET | /api/users/{id}/ | Yes | Retrieve user |
| PATCH/PUT | /api/users/{id}/ | Self or Admin | Update user |
| DELETE | /api/users/{id}/ | Self or Admin | Soft delete (status = inactive) |
| POST | /api/auth/login/ | No | Login with email + password (JWT) |
| POST | /api/auth/send-otp/ | No | Send OTP by email |
| POST | /api/auth/verify-otp/ | No | Verify OTP |
| POST | /api/auth/forgot-password/ | No | Send password-reset OTP |
| POST | /api/auth/reset-password/ | No | Reset password using OTP |
| POST | /api/auth/token/refresh/ | No | New access token |

Authenticated requests need the header `Authorization: Bearer <access token>`.

## Request Fields (POST /api/users/)
| Field | Required | Notes |
|---|---|---|
| username, email, password, confirm_password | Yes | email must be unique |
| first_name, last_name, nationality, phone, addresses, emergency_contact_* | No | |
| date_of_birth | No | YYYY-MM-DD |
| gender | No | male, female, other |
| blood_group | No | A+, A-, B+, B-, AB+, AB-, O+, O- |
| image | No | multipart/form-data only |

## Sample Requests and Responses
<paste register 201/400, login 200/401, send-otp, verify-otp,
reset-password and soft-delete examples from Postman. Mask tokens and use dummy data.>

## Design Decisions
- `username` is kept; login looks up the user by email (case-insensitive).
- Inactive (soft-deleted) users cannot log in and their tokens are rejected.
- New users start as Standard; only an Administrator can change profiles.
- Forgot-password answers "No such user exists" for unknown emails (this reveals
  registered emails; a generic message is safer in production).
- Older OTPs are invalidated when a new one is requested.

## Postman
Open Postman -> Import -> select the `postman` folder.