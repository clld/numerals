from pyramid.config import Configurator

# we must make sure custom models are known at database initialization!
from numerals import models


def _(s):
    return s


_('Language')
_('Languages')


# noinspection PyUnusedLocal
def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('clldmpg')
    return config.make_wsgi_app()
