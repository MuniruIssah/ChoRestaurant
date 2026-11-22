"""
Config package initialization.
Exposes Celery application when Celery is installed so shared tasks work across apps.
"""
try:
    from .celery import app as celery_app

    __all__ = ("celery_app",)
except ImportError:
    __all__ = ()
