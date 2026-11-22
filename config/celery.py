"""
Celery configuration for Restaurant Ordering & Delivery Management System.
Used by Developer 3, Developer 4, and Developer 5 for background tasks.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("restaurant_delivery")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
