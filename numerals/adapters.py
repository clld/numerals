import ete3
from clld import interfaces
from clld.web.adapters.cldf import CldfConfig
from clld_phylogeny_plugin.interfaces import ITree
from clld_phylogeny_plugin.tree import Tree
from clldutils.misc import lazyproperty
from ete3.coretype.tree import TreeError
from six import PY2
from sqlalchemy.orm import joinedload_all, joinedload
from numerals.models import Variety
from clld.db.models.common import Language

from numerals.models import get_color


class NumeralsCldfConfig(CldfConfig):
    module = 'StructureDataset'

    def custom_schema(self, req, ds):
        ds.add_columns(
            'LanguageTable',
            {'name': 'Family', 'datatype': 'string'})

    def convert(self, model, item, req):
        res = CldfConfig.convert(self, model, item, req)

        if model == Language:
            res['Macroarea'] = item.macroarea
            res['Family'] = item.family

        return res

    def query(self, model):
        q = CldfConfig.query(self, model)
        if model == Language:
            q = q.options(joinedload(Variety.family))
        return q


class NumeralbankTree(Tree):
    @lazyproperty
    def newick(self):
        if self.parameters:
            t = ete3.Tree(self.ctx.newick, format=1)
            nodes = set(
                n.encode('utf8') if PY2 else n for n in self.labelSpec.keys())
            try:
                t.prune(
                    nodes.intersection(set(n.name for n in t.traverse())),
                    preserve_branch_length=False)
            except TreeError:
                raise
                return
            return t.write(format=1)
        return self.ctx.newick

    def get_marker(self, valueset):
        return 'c', get_color(valueset)


def includeme(config):
    config.registry.registerUtility(NumeralsCldfConfig(),
                                    interfaces.ICldfConfig)
    config.registry.registerUtility(NumeralbankTree, ITree)
