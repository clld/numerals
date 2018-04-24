"""
This module will be available in templates as ``u``.

This module is also used to lookup custom template context providers, i.e. functions
following a special naming convention which are called to update the template context
before rendering resource's detail or index views.
"""

from clld.web.util.multiselect import CombinationMultiSelect


def phylogeny_detail_html(request=None, context=None, **kw):
    return {
        'ms': CombinationMultiSelect,
    }
