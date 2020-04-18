from clld.web.util.multiselect import CombinationMultiSelect
from clld.db.meta import DBSession
from clld.db.models.common import Language, Identifier, LanguageIdentifier, IdentifierType
from clld.web.util.htmllib import HTML

def phylogeny_detail_html(request=None, context=None, **kw):
    return {"ms": CombinationMultiSelect}

def get_variety_links(request=None, context=None, **kw):
    if context.glottocode:
        q = DBSession.query(Language.id, Language.name)\
            .join(LanguageIdentifier, Identifier)\
            .filter(Identifier.name == context.glottocode,
                Identifier.type == IdentifierType.glottolog.value,
                Language.id != context.id).all()
        if len(q) == 0:
            return ("", "")
        res = ""
        title_string = "Further variet"
        title_string += "ies " if len(q) > 1 else "y "
        title_string += "linked to Glottocode “{0}”".format(context.glottocode)
        for l in q:
            res += HTML.li(HTML.a(l[1], href=l[0]))
        return (HTML.ul(res), title_string)
    return ("", "")
