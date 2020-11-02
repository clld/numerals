from clld.web.util.multiselect import CombinationMultiSelect
from clld.db.meta import DBSession
from clld.db.models.common import Language, Identifier, LanguageIdentifier, IdentifierType
from clld.web.util.htmllib import HTML


def phylogeny_detail_html(request=None, context=None, **kw):
    return {"ms": CombinationMultiSelect}


def get_variety_links(request=None, context=None, idtype='glottocode', **kw):
    if idtype == "glottocode":
        IType = IdentifierType.glottolog.value
        typename = "Glottocode"
    elif idtype == "iso_code":
        IType = IdentifierType.iso.value
        typename = "ISO code"
    else:
        return ("", "")

    if getattr(context, idtype, False):
        q = DBSession.query(Language.id, Language.name)\
            .join(LanguageIdentifier, Identifier)\
            .filter(Identifier.name == getattr(context, idtype),
                    Identifier.type == IType,
                    Language.id != context.id).distinct().all()
        if len(q) == 0:
            return ("", "")
        res = ""
        title_string = "Further variet"
        title_string += "ies " if len(q) > 1 else "y "
        title_string += "linked to {1} “{0}”".format(getattr(context, idtype), typename)
        for lg in q:
            res += HTML.li(HTML.a(lg[1], href=lg[0]))
        return (HTML.ul(res), title_string)
    return ("", "")
