__all__ = ['create_app', 'FmtDomains']

from .core import create_app, FmtDomains


def run():
    app = create_app()
    app.run()
