from clld import interfaces
from clld.db.meta import CustomModelMixin
from clld.db.models.common import Language, ValueSet, Value, DomainElement, Parameter
from clld_glottologfamily_plugin.models import HasFamilyMixin
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
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
    is_loan = Column(Boolean, default=False)
    comment = Column(Unicode)
    is_problematic = Column(Boolean, default=False)


@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, Language, HasFamilyMixin):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
    creator = Column(Unicode)

class NumberParameter(CustomModelMixin, Parameter):
    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)
    concepticon_id = Column(Integer)
