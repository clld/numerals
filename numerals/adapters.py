import ete3
from clld import interfaces
from clld.web.adapters.cldf import CldfConfig
from clld.web.adapters.geojson import GeoJsonLanguages
from clld.web.util.htmllib import HTML
from clld.web.util.helpers import link
from clld_phylogeny_plugin.interfaces import ITree
from clld_phylogeny_plugin.tree import Tree
from clldutils.misc import lazyproperty
from ete3.coretype.tree import TreeError
from sqlalchemy.orm import joinedload
from numerals.models import Variety, get_color
from clld.db.models.common import (
    Parameter, ValueSet, Language, LanguageIdentifier, Identifier, IdentifierType)
from clld.db.meta import DBSession
from collections import defaultdict


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
    def glottolog2language_ids(self):
        gl2langids = defaultdict(list)
        for p in DBSession.query(Identifier.name, LanguageIdentifier.language_pk)\
                .join(Identifier)\
                .filter(Identifier.type == IdentifierType.glottolog.value):
            gl2langids[p[0]].append(p[1])
        return gl2langids

    @lazyproperty
    def langpk2language(self):
        return dict(p for p in DBSession.query(Language.pk, Language))

    @lazyproperty
    def pruned_newick(self):
        t = ete3.Tree(self.ctx.newick, format=1)
        try:
            t_dict = dict([n.name, n] for n in t.traverse())
            to_keep = set(
                t_dict[l.name] for l in self.ctx.treelabels
                if l.name in t_dict and any(
                    lang.pk in self.language2valueset for lang in l.languages))
            _, node2path = t.get_common_ancestor(to_keep, get_path=True)
            to_keep.add(t)
            n2count = {}
            visitors2nodes = {}
            for seed, path in node2path.items():
                for visited_node in path:
                    if visited_node is not seed:
                        n2count.setdefault(visited_node, set()).add(seed)
            for node, visitors in n2count.items():
                if len(visitors) > 1:
                    visitor_key = frozenset(visitors)
                    visitors2nodes.setdefault(visitor_key, set()).add(node)
            for visitors, nodes in visitors2nodes.items():
                if not (to_keep & nodes):
                    to_keep.add(list(nodes)[0])
            for n in t.get_descendants('postorder'):
                if n not in to_keep:
                    n.delete(prevent_nondicotomic=False)
        except TreeError:
            return ''

        return t.write(format=1)

    def comp(self, a, b, has_domain):
        if has_domain:
            return a.domainelement_pk == b.domainelement_pk
        return a.name == b.name

    def all_equal(self, iterator, has_domain):
        iterator = iter(iterator)
        try:
            first = next(iterator)
        except StopIteration:
            return True
        return all(self.comp(first, rest, has_domain) for rest in iterator)

    def _lg_link(self, req, obj, **kw):
        kw.setdefault('id', getattr(obj, 'id', obj))
        href = req.route_url('language', **kw)
        return HTML.a(str(obj), href=href)

    def get_label_properties(self, label, pindex=None):

        def vname(v):
            try:
                return domain[v.domainelement_pk].name
            except KeyError:
                return v.name

        res = {
            'eid': 'tlpk{0}-{1}'.format(label, pindex),
            'shape': 'c',
            'color': '#ff6600',
            'conflict': False,
            'tooltip_title': 'Related ' + self.req.translate('Languages'),
        }
        if pindex is not None:
            parameter = self.parameters[pindex]
            domain = self.domains[pindex]
            values = []
            color = '#ff6600'
            for lpk in self.glottolog2language_ids[label.name]:
                try:
                    vs = self.language2valueset[lpk][pindex]
                    values.extend(vs.values)
                    color = get_color(vs)
                except (KeyError, AttributeError):
                    continue
            if not values:
                res['tooltip_title'] = 'Missing data'
                res['tooltip'] = None
                res['shape'] = 's'
                res['color'] = '#fff'
            else:
                res['conflict'] = not self.all_equal(values, bool(parameter.domain))
                res['tooltip_title'] = 'Parameter ' + parameter.id
                lis = []
                for v in values:
                    lis.append(HTML.li(
                        vname(v) + ': ',
                        self._lg_link(self.req, v.valueset.language)))
                res['tooltip'] = HTML.ul(*lis, class_='unstyled')
                res['shape'] = 'c'
                res['color'] = color

        else:
            lis = []
            for lpk in self.glottolog2language_ids[label.name]:
                lis.append(HTML.li(self._lg_link(self.req, self.langpk2language[lpk])))
            res['tooltip'] = HTML.ul(*lis)
        return res

    @lazyproperty
    def newick(self):
        if self.parameters:
            return self.pruned_newick
        return self.ctx.newick


class NumeralGeoJsonLanguages(GeoJsonLanguages):
    def feature_iterator(self, ctx, req):
        return ctx.get_query(limit=10000)


def includeme(config):
    config.registry.registerUtility(NumeralsCldfConfig(),
                                    interfaces.ICldfConfig)
    config.registry.registerUtility(NumeralbankTree, ITree)
    config.register_adapter(NumeralGeoJsonLanguages,
                            interfaces.ILanguage)
