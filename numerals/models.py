from clld import interfaces
from clld.db.meta import CustomModelMixin
from clld.db.models.common import Language, ValueSet, Value, DomainElement, Parameter, Contribution, Source
from clld_glottologfamily_plugin.models import HasFamilyMixin
from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    ForeignKey,
    Unicode
)
from sqlalchemy.orm import relationship, backref
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
    other_form = Column(Unicode)
    org_form = Column(Unicode)
    comment = Column(Unicode)
    is_problematic = Column(Boolean, default=False)


@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, Language, HasFamilyMixin):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
    creator = Column(Unicode)
    comment = Column(Unicode)
    url_soure_name = Column(Unicode)
    contrib_name = Column(Unicode)


@implementer(interfaces.IParameter)
class NumberParameter(CustomModelMixin, Parameter):
    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)
    concepticon_id = Column(Integer)
    count_of_datapoints = Column(Integer)
    count_of_varieties = Column(Integer)


@implementer(interfaces.IContribution)
class Provider(CustomModelMixin, Contribution):
    pk = Column(Integer, ForeignKey('contribution.pk'), primary_key=True)
    url = Column(Unicode)
    license = Column(Unicode)
    aboutUrl = Column(Unicode)
    accessURL = Column(Unicode)
    version = Column(Unicode)
    doi = Column(Unicode)
    language_count = Column(Integer)
    parameter_count = Column(Integer)
    lexeme_count = Column(Integer)


@implementer(interfaces.ISource)
class NumberSource(CustomModelMixin, Source):
    pk = Column(Integer, ForeignKey('source.pk'), primary_key=True)
    provider_pk = Column(Integer, ForeignKey('provider.pk'))
    provider = relationship(Provider, backref='sources')
