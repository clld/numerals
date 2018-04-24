import ete3
from clld_phylogeny_plugin.interfaces import ITree
from clld_phylogeny_plugin.tree import Tree
from clldutils.misc import lazyproperty
from ete3.coretype.tree import TreeError
from six import PY2

from numerals.models import get_color


class NumeralbankTree(Tree):
    @lazyproperty
    def newick(self):
        if self.parameters:
            t = ete3.Tree(self.ctx.newick, format=1)
            nodes = set(n.encode('utf8') if PY2 else n for n in self.labelSpec.keys())
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
    config.registry.registerUtility(NumeralbankTree, ITree)
