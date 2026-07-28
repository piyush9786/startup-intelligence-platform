"""Environment-specific Django settings package.

Import a concrete module explicitly:

- ``config.settings.development`` for local development
- ``config.settings.test`` for tests
- ``config.settings.production`` for deployed services

Keeping this package empty prevents an accidental import from silently enabling
development settings in a production process.
"""
