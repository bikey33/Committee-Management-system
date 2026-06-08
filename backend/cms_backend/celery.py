import os
from celery import Celery


# Set default Django settings for Celery workers
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_backend.settings')

# Create Celery application
app = Celery('cms_backend')

# Load configuration from Django settings using the CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py modules in installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
	print(f'Request: {self.request!r}')


