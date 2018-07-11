from functools import partial

from clld.interfaces import IMapMarker
from clld.lib.svg import data_url, icon
from clld.web.app import menu_item
from clld.web.icon import MapMarker
from pyramid.config import Configurator

# we must make sure custom models are known at database initialization!
from numerals import models


class NumeralsMapMarker(MapMarker):
    def __call__(self, ctx, req):
        color = models.get_color(ctx)

        if not color:
            return MapMarker.__call__(self, ctx, req)

        return data_url(icon('c' + color))


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
    config.include('clld_phylogeny_plugin')
    config.registry.registerUtility(NumeralsMapMarker(), IMapMarker)
    config.register_menu(
        ('dataset', partial(menu_item, 'dataset', label='Home')),
        ('contributions',
         partial(menu_item, 'contributions', label='Contributions')),
        ('parameters', partial(menu_item, 'parameters', label='Numerals')),
        ('languages', partial(menu_item, 'languages', label='Languages')),
        ('contributors',
         partial(menu_item, 'contributors', label='Contributors')),
    )
    return config.make_wsgi_app()
