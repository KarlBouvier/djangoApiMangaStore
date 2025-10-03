from django.apps import AppConfig


class ProduitConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'produit'

    def ready(self):
        # Import signals to register handlers
        from . import signals  # noqa: F401
