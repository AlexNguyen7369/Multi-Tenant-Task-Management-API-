import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("config")

# Reads CELERY_* settings from Django settings.py (namespace="CELERY" means
# CELERY_BROKER_URL in settings.py becomes app.conf.broker_url, etc.).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discovers tasks.py in each installed app.
app.autodiscover_tasks()
