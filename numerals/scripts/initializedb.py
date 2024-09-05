import ete3
import json
import pycldf
import re
import unicodedata
import itertools

from clldutils import color
from clldutils.misc import slug
from clldutils.path import Path
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib.bibtex import Database
from clld.cliutil import Data, add_language_codes, bibtex2source
from clld_glottologfamily_plugin.util import load_families
from clld_glottologfamily_plugin.models import Family
from clld_phylogeny_plugin.models import Phylogeny, LanguageTreeLabel, TreeLabel
from sqlalchemy import func
from datetime import date
from pycldf import Wordlist
from pyconcepticon import Concepticon
from pylexibank import progressbar

import numerals
from numerals import models
from numerals.scripts.global_tree import tree


NUMERALS_RDFID = 'numerals'


def main(args):

    ds = args.cldf

    assert args.glottolog, 'The --glottolog option is required!'
    assert args.concepticon, 'The --concepticon option is required!'

    # get all concepts of numerals and convert them to integer ids
    concepticon_api = Concepticon(args.concepticon)
    number_concept_map = {
        c.id: re.sub(r'^.*?\((\d+)\).*$', r'\1', c.definition)
        for c in concepticon_api.conceptsets.values()
        if c.semanticfield == 'Quantity' and c.ontological_category == 'Number'
    }

    data = Data()

    dataset = common.Dataset(
        id=numerals.__name__,
        name="Numeralbank",
        description="Numeralbank",
        published=date(2023, 1, 19),
        publisher_name="Max Planck Institute for Evolutionary Anthropology",
        publisher_place="Leipzig",
        publisher_url="https://www.eva.mpg.de",
        license="https://creativecommons.org/licenses/by/4.0/",
        domain="numerals.clld.org",
        contact='dlce.rdm@eva.mpg.de',
        jsondata={
            "license_icon": "cc-by.png",
            "license_name": "Creative Commons Attribution 4.0 International License",
        },
    )

    DBSession.add(dataset)

    for i, (id_, name) in enumerate([
        ("barlowrussell", "Russell Barlow"),
        ("bellersieghard", "Sieghard Beller"),
        ("benderandrea", "Andrea Bender"),
        ("bibikohansjoerg", "Hans-Jörg Bibiko"),
        ("forkelrobert", "Robert Forkel"),
        ("greenhillsimon", "Simon Greenhill"),
        ("grayrussell", "Russell Gray"),
        ("hammarstroemharald", "Harald Hammarström"),
        ("jordanfiona", "Fiona Jordan"),
        ("rzymskichristoph", "Christoph Rzymski"),
        ("verkerkannemarie", "Annemarie Verkerk"),
    ]):
        ed = data.add(common.Contributor, id_, id=id_, name=name)
        common.Editor(dataset=dataset, contributor=ed, ord=i + 1)

    basis_parameter = data.add(
        models.NumberParameter,
        "-1",
        id="-1",
        name="Base",
    )
    DBSession.flush()

    valid_contribs = set()
    contribs = {}
    src_to_contrib_pks = {}
    for ct in ds["ContributionTable"]:
        doi = ''
        git_version = ''
        md = json.loads(ct["Metadata"])
        print(md)
        if md["doi"]:
            doi = md["doi"]
            accessURL = 'https://doi.org/{0}'.format(doi)
        else:
            git_version = md.get("git_version", None)
        accessURL = md.get("dcat:accessURL", None)
        valid_contribs.add(ct["ID"])
        contrib = models.Provider(
            id=ct["ID"],
            name=ct["Name"],
            description=ct.get("Citation", None),
            license=md.get('dc:license', None),
            aboutUrl=md.get('aboutUrl', None),
            accessURL=accessURL,
            version=git_version,
            doi=doi,
        )
        contribs[ct["ID"]] = contrib
        DBSession.add(contrib)

        DBSession.flush()

        if md["source"]:
            src_to_contrib_pks[md["source"]] = contrib.pk

    DBSession.flush()

    for rid, rec in enumerate(Database.from_file(ds.bibpath, lowercase=True)):
        rec_id = rec.id
        print(rec_id)
        if rec_id not in data['NumberSource']:
            ns = bibtex2source(rec, models.NumberSource)
            ns.provider_pk = src_to_contrib_pks[rec_id] if rec_id in src_to_contrib_pks else None
            ns.id = rec_id
            src = data.add(
                models.NumberSource,
                rec_id,
                _obj=ns,
            )
    DBSession.flush()

    ns = ds.column_names

    param_map = {}
    for parameter in ds["ParameterTable"]:
        if parameter[ns.parameters.concepticonReference] not in number_concept_map:
            continue
        #
        pid = number_concept_map[parameter[ns.parameters.concepticonReference]]
        param_map[parameter[ns.parameters.id]] = pid
        if pid not in data["NumberParameter"]:
            data.add(
                models.NumberParameter,
                pid,
                id=pid,
                name=pid,
                concepticon_id=parameter[ns.parameters.concepticonReference],
            )

    try:
        sep = ds["LanguageTable"].tableSchema.get_column(ns.languages.contributor).separator
    except AttributeError:
        sep = ""

    load_family_langs = []
    for language in ds["LanguageTable"]:

        if ns.languages.contributor in language:
            if sep:
                creator = '{0} '.format(sep).join(language[ns_languages_contributor])
            else:
                creator = language[ns_languages_contributor]
        else:
            creator = None

        lg_id = language[ns.languages.id]
        if lg_id not in data["Variety"]:
            _comm = language.get(ns.languages.comment, None)
            if _comm:
                com = "{}; {}".format(_comm, language["BaseComment"])
            else:
                comm = language["BaseComment"]
            cid = lg_id.split("-")[0]
            if cid not in valid_contribs:
                srgs.log.warn("{} not a valid contribution ID".format(cid))
            lang = data.add(
                models.Variety,
                lg_id,
                id=lg_id,
                name=language[ns.languages.name],
                latitude=language[ns.languages.latitude],
                longitude=language[ns.languages.longitude],
                contrib_name=cid,
                creator=creator,
                comment=comm,
                url_soure_name=language.get("SourceFile", None),
            )
            if language[ns.languages.glottocode]:
                load_family_langs.append((language[ns.languages.glottocode], lang))
            if language[ns.languages.iso639P3code]:
                add_language_codes(data, lang, language[ns.languages.iso639P3code])
        else:
            args.log.warn("Language ID '{0}' already exists".format(lg_id))

    # Add Base info if given
    for language in ds["LanguageTable"]:
        lg_id = language[ns.languages.id]
        if "BaseAnnotation" in language and language["BaseAnnotation"]:
            basis = language["BaseAnnotation"]
            de = data["DomainElement"].get(basis)
            if not de:
                de = data.add(
                    common.DomainElement,
                    basis,
                    id=str(basis),
                    name=str(basis),
                    parameter=basis_parameter,
                )
            vs = data.add(
                common.ValueSet,
                data["Variety"][lg_id].id,
                id="{0}-{1}".format(basis_parameter.id, data["Variety"][lg_id].id),
                language=data["Variety"][lg_id],
                parameter=basis_parameter,
                contribution=contribs[lg_id.split('-')[0]],
            )

            common.Value(
                id=data["Variety"][lg_id].id,
                valueset=vs,
                domainelement=de
            )

    DBSession.flush()

    for form in progressbar(ds["FormTable"], desc="Processing data"):

        if form[ns.forms.parameterReference] not in param_map:
            continue

        formpid = param_map[form[ns.forms.parameterReference]]
        valueset_id = "{0}-{1}".format(formpid, form[ns.forms.languageReference])
        valueset = data["ValueSet"].get(valueset_id)

        # Unless we already have something in the VS:
        if not valueset:
            lg_id = form[ns.forms.languageReference]
            if lg_id in data["Variety"]:
                src = None
                if form[ns.forms.source]:
                    src = ",".join(form[ns.forms.source])
                vs = data.add(
                    common.ValueSet,
                    valueset_id,
                    id=valueset_id,
                    language=data["Variety"][lg_id],
                    parameter=data["NumberParameter"][formpid],
                    contribution=contribs[form[ns.forms.languageReference].split("-")[0]],
                    source=src,
                )

        DBSession.add(
            models.NumberLexeme(
                id=form[ns.forms.id],
                name=form[ns.forms.form],
                comment=form[ns.forms.comment],
                is_loan=form["Loan"] if "Loan" in form else None,
                other_form=form[ns.forms.value],
                org_form=None,
                is_problematic=form["Problematic"] if "Problematic" in form else None,
                valueset=vs,
            )
        )

    DBSession.flush()

    args.log.info('Processing families')
    load_families(
        Data(),
        load_family_langs,
        glottolog_repos=args.glottolog,
        strict=False,
    )

    distinct_varieties = DBSession.query(models.Variety.family_pk).distinct().all()
    families = dict(
        zip([r[0] for r in distinct_varieties], color.qualitative_colors(len(distinct_varieties)))
    )

    for lg in DBSession.query(models.Variety):
        lg.jsondata = {"color": families[lg.family_pk]}

    p = common.Parameter.get("-1")
    colors = color.qualitative_colors(len(p.domain))

    for i, de in enumerate(p.domain):
        de.jsondata = {"color": colors[i]}


def prime_cache(args):

    # add number of data points per parameter
    for np in DBSession.query(common.Parameter, func.count(common.Parameter.pk)) \
            .join(common.ValueSet) \
            .join(common.Value) \
            .group_by(models.NumberParameter.pk, common.Parameter.pk):
        np[0].count_of_datapoints = np[1]

    # add number of distinct varieties per parameter based on assigned glottocodes
    for np in DBSession.query(models.NumberParameter, func.count(common.Identifier.name)) \
            .join(common.ValueSet) \
            .join(common.Value) \
            .join(common.Language, common.ValueSet.language_pk == common.Language.pk) \
            .join(common.LanguageIdentifier) \
            .join(common.Identifier) \
            .filter(common.Identifier.type == common.IdentifierType.glottolog.value) \
            .group_by(models.NumberParameter.pk, common.Parameter.pk):
        np[0].count_of_varieties = np[1]

    # add number of data points of parameter "base"
    base_pk, cnt_base = DBSession.query(common.Parameter.pk, func.count(common.ValueSet.pk)) \
        .join(common.Parameter) \
        .filter(common.Parameter.name == 'Base') \
        .group_by(common.Parameter.pk).all()[0]
    for np in DBSession.query(models.Parameter) \
            .filter(common.Parameter.pk == base_pk):
        np.count_of_datapoints = cnt_base
        break

    for prov in DBSession.query(models.Provider):
        q = DBSession.query(common.ValueSet.language_pk)\
            .filter(common.ValueSet.contribution_pk == prov.pk)\
            .distinct()
        prov.language_count = q.count()
        prov.update_jsondata(language_pks=[r[0] for r in q])

        pcnt = DBSession.query(common.ValueSet.parameter_pk) \
            .filter(common.ValueSet.contribution_pk == prov.pk) \
            .distinct() \
            .count()

        prov.parameter_count = pcnt
        lcnt = DBSession.query(common.Value.pk)\
            .join(common.ValueSet)\
            .filter(common.ValueSet.contribution_pk == prov.pk)\
            .count()
        if prov.id == 'numerals':
            # do not count 'base lexemes'
            lcnt -= cnt_base
        prov.lexeme_count = lcnt

    DBSession.query(LanguageTreeLabel).delete()
    DBSession.query(TreeLabel).delete()
    DBSession.query(Phylogeny).delete()

    langs = [lg for lg in DBSession.query(common.Language) if lg.glottocode]

    newick, _ = tree(
        [lg.glottocode for lg in langs], gl_repos=args.glottolog
    )

    try:
        with open(args.glottolog / '.zenodo.json') as f:
            gljson = json.load(f)
        gltree_description = gljson['description']
        gltree_version = ' (Glottolog {0})'.format(
            gljson['title'].split(' ')[-1:][0].strip())
    except (FileNotFoundError, AttributeError):
        gltree_description = ''
        gltree_version = ''

    phylo = Phylogeny(
        id="globaltree",
        name="Glottolog Global Tree{0}".format(gltree_version),
        newick=newick,
        description=gltree_description
    )

    for lg in langs:
        LanguageTreeLabel(
            language=lg,
            treelabel=TreeLabel(id="{0}-1".format(lg.id),
                                name=lg.glottocode,
                                phylogeny=phylo)
        )
    DBSession.add(phylo)

    families = DBSession.query(Family.pk, Family.name).all()
    p_pk = 1
    for f in families:
        langs_in_family = [lg for lg in langs if lg.family_pk == f[0]]
        if len(langs_in_family) == 0:
            continue
        nodes = set([lg.glottocode for lg in langs_in_family])
        try:
            if len(nodes) == 1:
                t = ete3.Tree("({0});".format(list(nodes)[0]), format=1)
            else:
                t = ete3.Tree(newick, format=1)
                t.prune(
                    nodes.intersection(set(n.name for n in t.traverse())),
                    preserve_branch_length=False)
        except ete3.coretype.tree.TreeError as e:
            args.log.info("No tree for '{0}' due to {1}".format(f[1], e))
            continue
        phylo = Phylogeny(
            id=slug(f[1]),
            name="{1} Tree{0}".format(gltree_version, f[1]),
            newick=t.write(format=9),
            description=gltree_description
        )
        p_pk += 1
        for lg in langs_in_family:
            LanguageTreeLabel(
                language=lg, treelabel=TreeLabel(id="{0}-{1}".format(lg.id, p_pk),
                                                 name=lg.glottocode, phylogeny=phylo)
            )
        DBSession.add(phylo)
