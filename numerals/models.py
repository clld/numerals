from clld import interfaces
from clld.db.meta import CustomModelMixin
from clld.db.models.common import Language, ValueSet, Value, DomainElement
from clld_glottologfamily_plugin.models import HasFamilyMixin
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Unicode
)
from zope.interface import implementer


def get_color(ctx):
    color = None

    if isinstance(ctx, ValueSet):
        value = ctx.values[0]
        if value.domainelement:
            color = value.domainelement.jsondata['color']
        else:
            color = ctx.language.jsondata['color']
    elif isinstance(ctx, Value):
        if ctx.domainelement:
            color = ctx.domainelement.jsondata['color']
        else:
            color = ctx.valueset.language.jsondata['color']
    elif isinstance(ctx, DomainElement):
        color = ctx.jsondata['color']
    elif isinstance(ctx, Language):
        color = ctx.jsondata['color']

    return color


@implementer(interfaces.IValue)
class NumberLexeme(CustomModelMixin, Value):
    pk = Column(Integer, ForeignKey('value.pk'), primary_key=True)
    comment = Column(Unicode)


@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, Language, HasFamilyMixin):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
