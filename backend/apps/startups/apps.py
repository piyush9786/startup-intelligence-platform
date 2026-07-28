from django.apps import AppConfig


class StartupsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.startups"

    def ready(self):
        # These models live in dedicated modules to keep the core startup
        # domain file maintainable while remaining part of the startups app.
        from . import (  # noqa: PLC0415
            expert_marketplace_admin,  # noqa: F401
            expert_marketplace_models,  # noqa: F401
            workspace_admin,  # noqa: F401
            workspace_models,  # noqa: F401
        )
