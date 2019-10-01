from clld.web.util.multiselect import CombinationMultiSelect

def phylogeny_detail_html(request=None, context=None, **kw):
    return {"ms": CombinationMultiSelect}
