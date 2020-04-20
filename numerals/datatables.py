from clld.db.models.common import (Language, Parameter, DomainElement, Value, Contribution,
    ValueSet, Identifier, LanguageIdentifier, IdentifierType)
from clld.db.util import icontains
from clld.web.datatables.base import LinkCol, DetailsRowLinkCol, LinkToMapCol, Col
from clld.web.datatables.language import Languages
from clld.web.datatables.parameter import Parameters
from clld.web.datatables.value import Values, ValueNameCol
from clld.web.util.glottolog import url
from clld.web.util.helpers import external_link
from clld_glottologfamily_plugin.datatables import FamilyCol
from clld_glottologfamily_plugin.models import Family
from clld_cognacy_plugin.datatables import ConcepticonCol
from clld_cognacy_plugin.util import concepticon_link
from sqlalchemy import Integer, and_
from sqlalchemy.sql.expression import cast

from numerals.models import Variety, NumberLexeme, NumberParameter


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
        return Value.name

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
        return cast(Parameter.id, Integer)


class NumeralValueCol(LinkCol):
    @staticmethod
    def order():
        return cast(Parameter.id, Integer)


class NumberConcepticonCol(ConcepticonCol):
    __kw__ = {"bSearchable": False, "bSortable": False}

    def format(self, item):
        if not hasattr(item, 'concepticon_id'):
            return ''
        return concepticon_link(self.dt.req, item)


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
            DetailsRowLinkCol(self, 'more'),
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
        return query.join(
            ValueSet.parameter,
            Value.valueset,
            ValueSet.contribution,
            ValueSet.language,
            ).join(Family, isouter=True)

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
                FamilyCol(
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
                Col(self,
                    "other_form",
                    model_col=NumberLexeme.other_form,
                ),
                Col(self,
                    "comment",
                    model_col=NumberLexeme.comment,
                ),
                BoolCol(self,
                    "is_loan",
                    sTitle="Loan?",
                    model_col=NumberLexeme.is_loan,
                ),
                LinkToMapCol(
                    self, "m", get_object=lambda i: i.valueset.language, sTitle="Map Link"
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
                Col(self,
                    "other_form",
                    model_col=NumberLexeme.other_form,
                ),
                Col(self,
                    "comment",
                    model_col=NumberLexeme.comment,
                ),
                BoolCol(self,
                    "is_loan",
                    sTitle="Loan?",
                    model_col=NumberLexeme.is_loan,
                ),
            ]


def includeme(config):
    config.register_datatable("languages", Varieties)
    config.register_datatable("parameters", Numerals)
    config.register_datatable("values", Datapoints)
