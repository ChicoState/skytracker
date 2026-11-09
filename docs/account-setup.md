# Account setup

## Objective

Provide session-based accounts for SkyTracker. People sign up and log in with a
unique email address, manage a small set of personalization settings, and can
only view their own future saved data.

## Account parameters

`email` is the login identifier. `zip_code` and `birth_date` are required so
SkyTracker can tailor location-based information and date-specific events.
`first_name`, `last_name`, `timezone`, and `email_notifications` are optional
profile parameters. Passwords are hashed by Django and are never stored as
application data.

## Commands

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
docker compose exec server python manage.py migrate
docker compose exec server python manage.py createsuperuser
```

Run tests with:

```powershell
docker compose exec server python manage.py test
```

## Boundaries

- Always use Django's password and session utilities.
- Always collect ZIP code and birth date before creating an account.
- Always restrict future saved data with a foreign key to `settings.AUTH_USER_MODEL`.
- Do not use the legacy JSON storage for accounts.
- Password reset is currently handled directly in the application without email
  delivery or reset-token storage.

## Success criteria

- A person can sign up, log in, log out, and update profile settings.
- Email is the authentication identifier and is unique without regard to case.
- Unauthenticated visitors are redirected away from the profile page.
- Tests cover account creation, login, logout, and profile access.

## Password recovery

The login page includes a “Forgot your password?” link. A person enters the
email address for an existing account and chooses a new password directly.
No reset email, token, or email-provider configuration is used.

## Saved events

Authenticated users can save and delete their own event records at
`/accounts/saved-events/`. Each record stores an application event identifier
and an optional label. Records are linked to the account with a foreign key;
queries and deletes are restricted to the logged-in owner.
