from django.apps import AppConfig


class CommitteeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'committee'

    def ready(self):
        import committee.signals  # noqa: F401 - register signal handlers
