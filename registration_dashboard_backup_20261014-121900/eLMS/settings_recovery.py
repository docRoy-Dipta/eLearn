from .settings import *

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "recovery_schema.sqlite3",
    }
}
