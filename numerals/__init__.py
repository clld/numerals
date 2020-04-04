from functools import partial

from clld.interfaces import IMapMarker
from clldutils import svg
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

        return svg.data_url(svg.icon('c' + color))


_ = lambda s: s
_('Parameter')
_('Parameters')
_('Phylogeny')
_('Phylogenys')

# noinspection PyUnusedLocal
def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('clldmpg')
    config.include('clld_phylogeny_plugin')
    config.include('clld_cognacy_plugin')
    config.registry.registerUtility(NumeralsMapMarker(), IMapMarker)
    return config.make_wsgi_app()
