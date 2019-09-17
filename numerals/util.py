from clld.web.util.multiselect import CombinationMultiSelect


def get_concepticon_link(request, meaning):
    return HTML.a(
        HTML.img(
            src=request.static_url("numerlas:static/concepticon_logo.png"), height=20, width=30
        ),
        title="Concepticon Link",
        href=meaning.concepticon_url,
    )


def phylogeny_detail_html(request=None, context=None, **kw):
    return {"ms": CombinationMultiSelect}
