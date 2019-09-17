from clld.db.models.common import Language, Parameter, DomainElement
from clld.web.datatables.base import LinkCol, DetailsRowLinkCol, LinkToMapCol, Col
from clld.web.datatables.language import Languages
from clld.web.datatables.parameter import Parameters
from clld.web.datatables.value import Values, ValueNameCol
from clld_glottologfamily_plugin.datatables import FamilyCol
from sqlalchemy import Integer
from sqlalchemy.sql.expression import cast

from numerals.models import Variety
from numerals.util import get_concepticon_link


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


class NumeralsComment(Col):
    # TODO: Placeholder, until Lexibank data is in place.
    def col_defs(self):
        return ""


class ConcepticonCol(Col):
    # TODO: Placeholder, until Lexibank data is in place.
    __kw__ = {"bSearchable": False, "bSortable": False}

    @staticmethod
    def col_defs(self):
        return ""


class Varieties(Languages):
    def col_defs(self):
        return Languages.col_defs(self) + [FamilyCol(self, "Family", Variety)]


class Numerals(Parameters):
    def get_options(self):
        opts = super(Parameters, self).get_options()
        opts["aaSorting"] = [[0, "asc"], [1, "asc"]]

        return opts

    def col_defs(self):
        return [NumeralParameterCol(self, "number"), ConcepticonCol(self, "concepticon")]


class Datapoints(Values):
    def get_options(self):
        opts = super(Values, self).get_options()
        opts["aaSorting"] = [[0, "asc"], [1, "asc"]]

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
                ValueNameCol(self, "value"),
                NumeralValueCol(
                    self,
                    "parameter",
                    model_col=Parameter.id,
                    get_object=lambda i: i.valueset.parameter,
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
                    model_col=Parameter.id,
                    get_object=lambda i: i.valueset.parameter,
                ),
                ValueNameCol(self, "value"),
                NumeralsComment(self, "comment"),
            ]


def includeme(config):
    config.register_datatable("languages", Varieties)
    config.register_datatable("parameters", Numerals)
    config.register_datatable("values", Datapoints)
