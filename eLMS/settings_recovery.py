from .settings import *

import os
SECRET_KEY = os.environ["ELEARN_RECOVERY_SECRET_KEY"]

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "recovery_schema.sqlite3",
    }
}


# Recovery-only security hardening. The original settings.py remains unchanged.
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.contrib.sessions.middleware.SessionMiddleware") + 1,
    "django.middleware.csrf.CsrfViewMiddleware",
)
