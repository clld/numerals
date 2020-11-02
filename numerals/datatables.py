from clld.db.models.common import (
    Language, Parameter, DomainElement, Value, Contribution,
    ValueSet, Identifier, LanguageIdentifier, IdentifierType, Source
)
from clld.db.meta import DBSession
from clld.db.util import icontains, collkey
from clld.web.datatables.base import LinkCol, DetailsRowLinkCol, LinkToMapCol, Col
from clld.web.datatables.language import Languages
from clld.web.datatables.parameter import Parameters
from clld.web.datatables.source import Sources, TypeCol
from clld.web.datatables.contribution import Contributions, CitationCol
from clld.web.datatables.value import Values, ValueNameCol
from clld.web.util.glottolog import url
from clld.web.util.helpers import external_link, map_marker_img
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.datatables import FamilyCol
from clld_glottologfamily_plugin.models import Family
from clld_cognacy_plugin.datatables import ConcepticonCol
from clld_cognacy_plugin.util import concepticon_link
from sqlalchemy import BigInteger, and_, func
from sqlalchemy.sql.expression import cast
from sqlalchemy.orm import joinedload

from numerals.models import Variety, NumberLexeme, NumberParameter, Provider


class BoolCol(Col):
    def format(self, item):
        v = str(self.get_value(item))
        if v == 'True':
            return '<span style="display:block; text-align:center; margin:0 auto;">✓</span>'
        return ''


class NumeralGlottocodeCol(Col):
    __kw__ = {"bSortable": False}

    def format(self, item):
        if item.glottocode:
            return external_link(
                url=url(item.glottocode),
                label=item.glottocode,
                title="View languoid {0} at Glottolog".format(item.glottocode),
                target="_new")
        else:
            return ""

    def search(self, qs):
        return and_(Identifier.type.__eq__(IdentifierType.glottolog.value),
                    icontains(Identifier.name, qs))


class NumeralISOCol(Col):
    __kw__ = {"bSortable": False}

    def format(self, item):
        return item.iso_code

    def search(self, qs):
        return and_(Identifier.type.__eq__(IdentifierType.iso.value),
                    icontains(Identifier.name, qs))


class NumeralValueNameCol(ValueNameCol):
    def order(self):
        return collkey(func.translate(Value.name, 'ˈ,ː,ˌ', ''))

    def format(self, item):
        if item.domainelement:
            if self.dt.language:
                return item.domainelement.name
            else:
                return HTML.div(map_marker_img(
                    self.dt.req, self.get_obj(item)), ' ', item.domainelement.name)
        return super(NumeralValueNameCol, self).format(item)

    def search(self, qs):
        if self.dt.parameter and self.dt.parameter.name == 'Base':
            return icontains(DomainElement.name, qs)
        else:
            return icontains(Value.name, qs)


class NumeralParameterCol(LinkCol):
    @staticmethod
    def get_attrs(item):
        return {"label": item}

    @staticmethod
    def order():
        return cast(Parameter.id, BigInteger)


class NumeralValueCol(LinkCol):
    @staticmethod
    def order():
        return cast(Parameter.id, BigInteger)


class NumberConcepticonCol(ConcepticonCol):
    __kw__ = {"bSearchable": False, "bSortable": False}

    def format(self, item):
        if not hasattr(item, 'concepticon_id'):
            return ''
        return concepticon_link(self.dt.req, item)


class NumeralContributionCol(Col):

    def search(self, qs):
        return icontains(Contribution.id, qs)


class NumberConcepticonCol(ConcepticonCol):
    __kw__ = {"bSearchable": False, "bSortable": False}

    def format(self, item):
        if not hasattr(item, 'concepticon_id'):
            return ''
        return concepticon_link(self.dt.req, item)


class NumeralFamilyCol(FamilyCol):
    def format(self, item):
        if self.dt.parameter and self.dt.parameter.name == 'Base':
            item = self.get_obj(item)
            if item.family:
                return item.family.name
            return 'isolate'
        return super(NumeralFamilyCol, self).format(item)


class ProviderCol(Col):
    __kw__ = {
        'choices': [
            r.id for r in DBSession.query(Contribution).order_by(Contribution.id)
        ]
    }


class NumeralSources(Sources):
    def get_options(self):
        opts = super(Sources, self).get_options()
        opts["aaSorting"] = [[1, "asc"]]
        return opts

    def base_query(self, query):
        return query.join(Contribution)

    def col_defs(self):
        return [
            DetailsRowLinkCol(self, 'd'),
            LinkCol(self, 'name'),
            Col(self, 'description', sTitle='Title', format=lambda i: HTML.span(i.description)),
            Col(self, 'year'),
            Col(self, 'author'),
            TypeCol(self, 'bibtex_type'),
            ProviderCol(
                self,
                'contribution',
                model_col=Contribution.id,
                get_object=lambda i: i.provider,
            ),
        ]


class NumeralContributions(Contributions):
    def col_defs(self):
        return [
            Col(self, 'id'),
            LinkCol(self, 'name'),
            Col(
                self,
                'language_count',
                model_col=Provider.language_count,
                sTitle='# languages',
                sTooltip='Number of languages'
            ),
            Col(
                self,
                'parameter_count',
                model_col=Provider.parameter_count,
                sTitle='# numerals',
                sTooltip='Number of numeral concepts'
            ),
            Col(
                self,
                'lexeme_count',
                model_col=Provider.lexeme_count,
                sTitle='# lexemes',
                sTooltip='Number of lexemes'
            ),
            CitationCol(self, 'cite'),
        ]


class Varieties(Languages):
    def base_query(self, query):
        return query.distinct().join(Variety.family, isouter=True)\
            .join(*Variety.identifiers.attr, isouter=True)

    def col_defs(self):
        return [
            LinkCol(
                self,
                'name'
            ),
            LinkToMapCol(
                self,
                'm'
            ),
            NumeralGlottocodeCol(
                self,
                'Glottocode'
            ),
            NumeralISOCol(
                self,
                'ISO',
                sTitle='ISO 639-3'
            ),
            Col(
                self,
                'latitude',
                sDescription='<small>The geographic latitude</small>'
            ),
            Col(
                self,
                'longitude',
                sDescription='<small>The geographic longitude</small>'
            ),
            FamilyCol(
                self,
                "Family",
                Variety
            ),
            ProviderCol(
                self,
                "contribution",
                model_col=Variety.contrib_name
            ),
        ]


class Numerals(Parameters):
    def get_options(self):
        opts = super(Parameters, self).get_options()
        opts["aaSorting"] = [[0, "asc"]]
        opts['iDisplayLength'] = 200
        return opts

    def col_defs(self):
        return [
            NumeralParameterCol(
                self,
                "numeral",
                model_col=Parameter.name,
            ),
            Col(
                self,
                "count_of_datapoints",
                sTitle='Number of data points',
                sTooltip='number of data points per numeral',
                model_col=NumberParameter.count_of_datapoints,
            ),
            Col(
                self,
                "count_of_varieties",
                sTitle='Number of distinct varieties',
                sTooltip='number of distinct varieties based on assigned Glottocodes',
                model_col=NumberParameter.count_of_varieties,
            ),
            NumberConcepticonCol(
                self,
                "concepticon_id",
                model_col=NumberParameter.concepticon_id,
                sTitle='',
                sWidth=40,
            )
        ]


class Datapoints(Values):
    def base_query(self, query):
        query = Values.base_query(self, query)
        if self.parameter:
            return query.join(Family, isouter=True).options(
                joinedload(Value.valueset).joinedload(ValueSet.language),
            )
        elif self.contribution:
            return query.options(
                joinedload(Value.valueset).joinedload(ValueSet.parameter),
                joinedload(Value.valueset).joinedload(ValueSet.language),
                joinedload(Value.valueset).joinedload(ValueSet.contribution),
                joinedload(Value.domainelement),
            )
        else:
            return query

    def get_options(self):
        opts = super(Values, self).get_options()
        if self.parameter:
            opts["aaSorting"] = [[1, "asc"], [2, "asc"], [0, "asc"]]
        else:
            opts["aaSorting"] = [[0, "asc"]]

        return opts

    def col_defs(self):
        if self.parameter:
            return [
                LinkCol(
                    self,
                    "language",
                    model_col=Language.name,
                    get_object=lambda i: i.valueset.language,
                ),
                NumeralFamilyCol(
                    self,
                    "Family",
                    Variety,
                    get_object=lambda i: i.valueset.language
                ),
                NumeralValueNameCol(
                    self,
                    "form",
                    model_col=Value.name,
                ),
                ProviderCol(
                    self,
                    "contribution",
                    model_col=Variety.contrib_name,
                    get_object=lambda i: i.valueset.language
                ),
                Col(
                    self,
                    "other_form",
                    model_col=NumberLexeme.other_form,
                ),
                Col(
                    self,
                    "comment",
                    model_col=NumberLexeme.comment,
                ),
                BoolCol(
                    self,
                    "is_loan",
                    sTitle="Loan?",
                    model_col=NumberLexeme.is_loan,
                ),
                LinkToMapCol(
                    self,
                    "m",
                    get_object=lambda i: i.valueset.language,
                    sTitle="Map Link"
                ),
            ]
        else:
            return [
                NumeralValueCol(
                    self,
                    "parameter",
                    model_col=Parameter.name,
                    get_object=lambda i: i.valueset.parameter,
                ),
                NumeralValueNameCol(
                    self,
                    "form",
                    model_col=Value.name
                ),
                Col(
                    self,
                    "other_form",
                    model_col=NumberLexeme.other_form,
                ),
                Col(
                    self,
                    "comment",
                    model_col=NumberLexeme.comment,
                ),
                BoolCol(
                    self,
                    "is_loan",
                    sTitle="Loan?",
                    model_col=NumberLexeme.is_loan,
                ),
            ]


def includeme(config):
    config.register_datatable("languages", Varieties)
    config.register_datatable("parameters", Numerals)
    config.register_datatable("values", Datapoints)
    config.register_datatable("contributions", NumeralContributions)
    config.register_datatable("sources", NumeralSources)
