# Ensure the Celery app is loaded when Django starts so that shared_task
# definitions bind to the configured app (and CELERY_* settings, e.g. eager
# mode, take effect in the web process).
from .celery import app as celery_app

__all__ = ('celery_app',)
