import sys

from clldutils.path import Path
from clld.db.meta import DBSession
from clld.db.models import common
from clldutils import color
from clld.scripts.util import initializedb, Data, add_language_codes
from clld_glottologfamily_plugin.util import load_families
from clld_phylogeny_plugin.models import Phylogeny, LanguageTreeLabel, TreeLabel
from pycldf.dataset import Wordlist
from six import text_type

import numerals
from numerals import models
from numerals.scripts.global_tree import tree

gl_repos = Path(numerals.__file__).parent / '../..' / 'glottolog'
data_file_path = Path(numerals.__file__).parent / '../..' / 'channumerals'

ds = Wordlist.from_metadata(data_file_path / 'cldf' / 'cldf-metadata.json')


def main(args):
    print(args)

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
        common.Contribution, "channumerals", id="channumerals", name="Eugene Chan's Numerals"
    )

    # Parameters:
    for parameter in ds["ParameterTable"]:
        data.add(
            models.NumberParameter,
            parameter["ID"],
            id=parameter["ID"],
            name="{0}".format(parameter["ID"]),
            concepticon_id=parameter['Concepticon_ID'],
        )

    basis_parameter = data.add(common.Parameter, "0", id="0", name="Base")

    # Languages
    for language in ds["LanguageTable"]:
        lang = data.add(
            models.Variety,
            language["ID"],
            id=language["ID"],
            name=language["Name"])
        add_language_codes(data, lang, None, glottocode=language["Glottocode"])

        # Base info if given
        if language["Base"]:
            basis = language["Base"]
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
                data["Variety"][language["ID"]].id + "-p",
                id=data["Variety"][language["ID"]].id + "-p",
                language=data["Variety"][language["ID"]],
                parameter=basis_parameter,
                contribution=contrib,
            )

            common.Value(id=data["Variety"][language["ID"]].id + "-p", valueset=vs, domainelement=de)

    # Forms:
    for form in ds["FormTable"]:
        valueset_id = "{0}-{1}".format(form["Parameter_ID"], form["Language_ID"])
        valueset = data["ValueSet"].get(valueset_id)

        # Unless we already have something in the VS:
        if not valueset:
            vs = data.add(
                common.ValueSet,
                valueset_id,
                id=valueset_id,
                language=data["Variety"][form["Language_ID"]],
                parameter=data["NumberParameter"][form["Parameter_ID"]],
                contribution=contrib,
            )

        DBSession.add(
            models.NumberLexeme(
                id=form["ID"],
                name=form["Form"],
                comment=form["Comment"],
                is_loan=form["Loan"],
                valueset=vs,
            )
        )

    load_families(
        Data(),
        [(l.glottocode, l) for l in DBSession.query(common.Language)],
        glottolog_repos=gl_repos,
        strict=False,
    )

    distinct_varieties = DBSession.query(models.Variety.family_pk).distinct().all()
    families = dict(
        zip([r[0] for r in distinct_varieties], color.qualitative_colors(len(distinct_varieties)))
    )

    for l in DBSession.query(models.Variety):
        l.jsondata = {"color": families[l.family_pk]}

    p = common.Parameter.get("0")
    colors = color.qualitative_colors(len(p.domain))

    for i, de in enumerate(p.domain):
        de.jsondata = {"color": colors[i]}


def prime_cache(args):
    print(args)

    DBSession.query(LanguageTreeLabel).delete()
    DBSession.query(TreeLabel).delete()
    DBSession.query(Phylogeny).delete()

    newick, _ = tree(
        [l.glottocode for l in DBSession.query(common.Language) if l.glottocode], gl_repos=gl_repos
    )

    phylo = Phylogeny(id="phy", name="glottolog global tree", newick=newick)

    for l in DBSession.query(common.Language):
        if l.glottocode:
            LanguageTreeLabel(
                language=l, treelabel=TreeLabel(id=l.id, name=l.glottocode, phylogeny=phylo)
            )

    DBSession.add(phylo)


if __name__ == "__main__":  # pragma: no cover
    initializedb(create=main, prime_cache=prime_cache)
    sys.exit(0)
