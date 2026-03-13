from config.settings import *  # noqa: F401,F403

SECRET_KEY = "test-secret-key-for-testing-only"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405
