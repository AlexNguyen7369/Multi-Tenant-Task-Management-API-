# Makes the Celery app available as `from config import celery_app` so
# @shared_task-decorated functions elsewhere in the project pick it up
# automatically (see config/celery.py).
from .celery import app as celery_app

__all__ = ("celery_app",)
