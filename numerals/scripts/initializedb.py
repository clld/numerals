from __future__ import unicode_literals

import re
import string
import sys
import unicodedata
from itertools import groupby

import xlrd
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib.color import qualitative_colors
from clld.scripts.util import initializedb, Data
from clld_glottologfamily_plugin.util import load_families
from clld_phylogeny_plugin.models import Phylogeny, LanguageTreeLabel, TreeLabel
from clldutils.misc import slug
from six import text_type

import numerals
from numerals import models
from numerals.scripts.global_tree import tree

GL_REPO = "/home/rzymski@shh.mpg.de/Repositories/glottolog/glottolog"


def main(args):
    data = Data()

    dataset = common.Dataset(
        id=numerals.__name__,
        name="Numeralbank",
        publisher_name="Max Planck Institute for the Science of Human History",
        publisher_place="Jena",
        publisher_url="http://www.shh.mpg.de",
        license="http://creativecommons.org/licenses/by/4.0/",
        domain="numerals.clld.org",
        jsondata={
            "license_icon": "cc-by.png",
            "license_name": "Creative Commons Attribution 4.0 International License",
        },
    )

    DBSession.add(dataset)

    for i, (id_, name) in enumerate(
        [("verkerkannemarie", "Annemarie Verkerk"), ("rzymskichristoph", "Christoph Rzymski")]
    ):
        ed = data.add(common.Contributor, id_, id=id_, name=name)
        common.Editor(dataset=dataset, contributor=ed, ord=i + 1)

    DBSession.add(dataset)

    contrib = data.add(
        common.Contribution, "numerals", id="numerals", name="Eugene Chan's numerals"
    )

    header = [
        "name",
        "country",
        "iso",
        "glotto_name",
        "glotto_code",
        "lg_link",
        "audio",
        "source",
        "nr_sets",
        "variant",
    ]

    meta = {}

    for row in iter_sheet_rows("META", args.data_file("numeral_301216.xlsx")):
        row = dict(zip(header, row))
        meta[(row["lg_link"], row["variant"])] = row

    basis_parameter = data.add(common.Parameter, "0", id="0", name="Base")

    #  bases = Counter()
    for key, items in groupby(
        sorted(
            iter_sheet_rows("NUMERAL", args.data_file("numeral_301216.xlsx")),
            key=lambda r: (text_type(r[2]), text_type(r[3]), text_type(r[0])),
        ),
        lambda r: (r[2], int(r[3] or 1)),
    ):
        if key not in meta:
            continue

        lid = "{0}-{1}".format(*key)
        md = meta[key]

        if md["lg_link"] == "DangauraTharu.htm":
            continue
        elif md["lg_link"] == "LowSaxon-Twente.htm":
            continue
        elif md["lg_link"] == "LowSaxon.htm":
            continue

        data.add(
            models.Variety, lid, id=my_slug(lid), name=md["name"], description=md["glotto_code"]
        )
        # source, ref = sources.get(md['source']), None
        # if source:
        #     ds.add_sources(source)
        #     ref = source.id

        items_, basis = [], None
        for concept, rows in groupby(items, lambda n: int(n[0])):
            parameter = data["Parameter"].get(concept)

            if not parameter:
                parameter = data.add(
                    common.Parameter, concept, id=slug(text_type(concept)), name=concept
                )

            vs_id = data["Variety"][lid].id + "-" + parameter.id

            vs = data.add(
                common.ValueSet,
                vs_id,
                id=vs_id,
                language=data["Variety"][lid],
                parameter=parameter,
                contribution=contrib,
                # Comment=row[4] or None,
            )

            for k, row in enumerate(rows):
                if row[1]:
                    if not basis:
                        for item in items_:
                            # Look for substring, if match is found base -1.
                            if item in row[1]:
                                basis = concept - 1
                    items_.append(row[1])
                    common.Value(id=vs_id + "-" + str(k), name=row[1], valueset=vs)
        if basis:
            basis = int(basis)
            if basis <= 16:
                de = data["DomainElement"].get(basis)
                if not de:
                    de = data.add(
                        common.DomainElement,
                        basis,
                        id=text_type(basis),
                        name=text_type(basis),
                        parameter=basis_parameter,
                    )
                vs = data.add(
                    common.ValueSet,
                    data["Variety"][lid].id + "-p",
                    id=data["Variety"][lid].id + "-p",
                    language=data["Variety"][lid],
                    parameter=basis_parameter,
                    contribution=contrib,
                    # Comment=row[4] or None,
                )

                common.Value(id=data["Variety"][lid].id + "-p", valueset=vs, domainelement=de)

    load_families(
        Data(),
        [(l.description, l) for l in DBSession.query(common.Language)],
        glottolog_repos=GL_REPO,
        strict=False,
    )

    x = DBSession.query(models.Variety.family_pk).distinct().all()
    families = dict(zip([r[0] for r in x], qualitative_colors(len(x))))

    for l in DBSession.query(models.Variety):
        l.jsondata = {"color": families[l.family_pk]}

    p = common.Parameter.get("0")
    colors = qualitative_colors(len(p.domain))

    for i, de in enumerate(p.domain):
        de.jsondata = {"color": colors[i]}


def iter_sheet_rows(sname, fname):
    wb = xlrd.open_workbook(fname.as_posix())
    sheet = wb.sheet_by_name(sname)

    for i in range(sheet.nrows):
        if i > 0:
            yield [col.value for col in sheet.row(i)]


def my_slug(s, remove_whitespace=True, lowercase=True):
    res = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    if lowercase:
        res = res.lower()
    for c in string.punctuation:
        if c == "-":
            continue
        else:
            res = res.replace(c, "")
    res = re.sub("\s+", "" if remove_whitespace else " ", res)
    res = res.encode("ascii", "ignore").decode("ascii")
    return res


# noinspection PyUnusedLocal
def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
    DBSession.query(LanguageTreeLabel).delete()
    DBSession.query(TreeLabel).delete()
    DBSession.query(Phylogeny).delete()

    newick, _ = tree(
        [l.description for l in DBSession.query(common.Language) if l.description], gl_repos=GL_REPO
    )

    phylo = Phylogeny(id="phy", name="glottolog global tree", newick=newick)

    for l in DBSession.query(common.Language):
        if l.description:
            LanguageTreeLabel(
                language=l, treelabel=TreeLabel(id=l.id, name=l.description, phylogeny=phylo)
            )

    DBSession.add(phylo)


if __name__ == "__main__":  # pragma: no cover
    initializedb(create=main, prime_cache=prime_cache)
    sys.exit(0)
