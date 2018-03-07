from clld.web.datatables.language import Languages
from clld_glottologfamily_plugin.datatables import FamilyCol

from numerals.models import Variety


class Varieties(Languages):
    def col_defs(self):
        return Languages.col_defs(self) + [FamilyCol(self, 'Family', Variety)]


def includeme(config):
    config.register_datatable('languages', Varieties)
