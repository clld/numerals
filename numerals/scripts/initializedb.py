import unicodedata
import pylexibank
import re
from pyconcepticon import Concepticon
from clldutils.path import Path
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import collkey, with_collkey_ddl
from clld.lib.bibtex import Database
from clldutils import color
from clldutils.misc import slug
from clld.cliutil import Data, add_language_codes, bibtex2source
from clld_glottologfamily_plugin.util import load_families
from clld_glottologfamily_plugin.models import Family
from clld_phylogeny_plugin.models import Phylogeny, LanguageTreeLabel, TreeLabel
import pycldf
from six import text_type
from sqlalchemy import func, Index
from datetime import date
import json
import ete3

import numerals
from numerals import models
from numerals.scripts.global_tree import tree
from numerals.scripts.utils.helper import unique_id, git_last_commit_date, prepare_additional_datasets


with_collkey_ddl()


def main(args):

    # data_set_path contains the default dataset 'channumerals'
    # all additional datasets will be handled via the git-repo 'numeralbank-internal'

    # path of additional datasets
    internal_repo = Path(numerals.__file__).parent.parent.parent.parent / 'numeralbank' / 'numeralbank-internal'

    # path of the core datasets 'channumerals'
    data_set_path = Path(numerals.__file__).parent.parent.parent.parent / 'numeralbank'

    assert args.glottolog, 'The --glottolog option is required!'
    assert args.concepticon, 'The --concepticon option is required!'

    cache_dir = internal_repo / 'datasets'
    cache_dir.mkdir(exist_ok=True)

    submissions_path = internal_repo / 'submissions-internal'

    ds_metadata = prepare_additional_datasets(args, submissions_path, cache_dir)

    numeral_datasets = []

    # load core dataset to get original forms for numerals
    args.log.info('Loading form table from core dataset "channumerals"')
    numeral_datasets.append(
        pycldf.Dataset.from_metadata(
            str(data_set_path / 'channumerals' / 'cldf' / 'cldf-metadata.json'))["FormTable"])

    # add all other addition datasets and ignore datasets marked as 'skip'
    for ds in pycldf.iter_datasets(cache_dir):
        if str(ds.directory).endswith('/cldf'):
            ds_dir = ds_metadata['contrib_paths_map'].get(ds.directory.parent.name, ds.directory.parent.name)
            if ds_dir in ds_metadata['contrib_skips']:
                if ds_metadata['contrib_skips'][ds_dir]:
                    args.log.info('{0} will be skipped'.format(ds_dir))
                    continue
            numeral_datasets.append(ds)

    # get all concepts of numerals and convert them to integer ids
    concepticon_api = Concepticon(args.concepticon)
    number_concept_map = {
        c.id: re.sub(r'^.*?\((\d+)\).*$', r'\1', c.definition)
        for c in concepticon_api.conceptsets.values()
        if c.semanticfield == 'Quantity' and c.ontological_category == 'Number'
    }

    Index('ducet', collkey(func.translate(common.Value.name, 'ˈ,ː,ˌ', '')))\
        .create(DBSession.bind)

    data = Data()

    dataset = common.Dataset(
        id=numerals.__name__,
        name="Numeralbank",
        description="Numeralbank",
        published=date(2020, 11, 1),
        publisher_name="Max Planck Institute for Evolutionary Anthropology",
        publisher_place="Leipzig",
        publisher_url="https://www.eva.mpg.de",
        license="https://creativecommons.org/licenses/by/4.0/",
        domain="numerals.clld.org",
        contact='lingweb@shh.mpg.de',
        jsondata={
            "license_icon": "cc-by.png",
            "license_name": "Creative Commons Attribution 4.0 International License",
        },
    )

    DBSession.add(dataset)

    for i, (id_, name) in enumerate([
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
    load_family_langs = []

    DBSession.flush()

    DBSession.add(dataset)

    # iterate through all sets but ignore channumerals
    for ds in numeral_datasets[1:]:
        if ds.directory.parent.name in ds_metadata['contrib_paths_map']:
            ds_dir = ds_metadata['contrib_paths_map'][ds.directory.parent.name]
            args.log.info('Processing {0}'.format(ds_dir))
        else:
            args.log.warn('{0} was skipped due to unknown contrib_path'.format(
                ds.directory.parent.name))
            continue

        if ds_dir in ds_metadata['rdfids']:
            rdfID = ds_metadata['rdfids'][ds_dir]
        else:
            args.log.warn('{0} will be skipped - no "id" given'.format(ds_dir))
            continue

        doi = ''
        git_version = ''
        accessURL = ds.properties.get('dcat:accessURL')
        if ds_dir in ds_metadata['contrib_dois']:
            doi = ds_metadata['contrib_dois'][ds_dir]
            accessURL = 'https://doi.org/{0}'.format(doi)
        else:
            git_version = git_last_commit_date(ds.directory.parent)

        contrib = models.Provider(
            id=rdfID,
            name=ds.properties.get('dc:title'),
            description=ds.properties.get('dc:bibliographicCitation'),
            url=ds.properties.get('dc:identifier'),
            license=ds.properties.get('dc:license'),
            aboutUrl=ds.properties.get('aboutUrl'),
            accessURL=accessURL,
            version=git_version,
            doi=doi,
        )
        DBSession.add(contrib)
        DBSession.flush()

        for rid, rec in enumerate(Database.from_file(ds.bibpath, lowercase=True)):
            rec_id = unique_id(rdfID, rec.id)
            if rec_id not in data['NumberSource']:
                ns = bibtex2source(rec, models.NumberSource)
                ns.provider_pk = contrib.pk
                ns.id = rec_id
                src = data.add(
                    models.NumberSource,
                    rec_id,
                    _obj=ns,
                )
        DBSession.flush()

        param_map = {}
        for parameter in ds["ParameterTable"]:
            if "Concepticon_ID" not in parameter\
                    or parameter["Concepticon_ID"] not in number_concept_map:
                continue

            pid = number_concept_map[parameter["Concepticon_ID"]]
            param_map[parameter["ID"]] = pid
            if pid not in data["NumberParameter"]:
                data.add(
                    models.NumberParameter,
                    pid,
                    id=pid,
                    name=pid,
                    concepticon_id=parameter["Concepticon_ID"],
                )

        for language in ds["LanguageTable"]:
            # make language IDs unique cross datasets
            lg_id = unique_id(rdfID, language["ID"])
            if lg_id not in data["Variety"]:
                lang = data.add(
                    models.Variety,
                    lg_id,
                    id=lg_id,
                    name=language["Name"],
                    latitude=language["Latitude"],
                    longitude=language["Longitude"],
                    contrib_name=rdfID,
                    creator=language["Contributor"] if "Contributor" in language else None,
                    comment=language["Comment"] if "Comment" in language else None,
                    url_soure_name=language["SourceFile"] if "SourceFile" in language else None,
                )
                if language["Glottocode"]:
                    load_family_langs.append((language["Glottocode"], lang))
                if language["ISO639P3code"]:
                    add_language_codes(data, lang, language["ISO639P3code"])
            else:
                args.log.warn("Language ID '{0}' already exists".format(lg_id))

        if rdfID == 'numerals':
            # get orginal forms for numerals
            org_forms = {f["ID"]: f for f in numeral_datasets[0]}

        # Add Base info if given
        for language in ds["LanguageTable"]:
            # make language IDs unique cross datasets
            lg_id = unique_id(rdfID, language["ID"])
            if "Base" in language and language["Base"]:
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
                    data["Variety"][lg_id].id,
                    id="{0}-{1}".format(basis_parameter.id, data["Variety"][lg_id].id),
                    language=data["Variety"][lg_id],
                    parameter=basis_parameter,
                    contribution=contrib,
                )

                common.Value(
                    id=data["Variety"][lg_id].id,
                    valueset=vs,
                    domainelement=de
                )

        other_form_warning = False
        for form in pylexibank.progressbar(ds["FormTable"], desc="reading {0}".format(rdfID)):

            if form["Parameter_ID"] not in param_map:
                continue

            formpid = param_map[form["Parameter_ID"]]

            valueset_id = "{0}-{1}-{2}".format(formpid, rdfID, form["Language_ID"])
            valueset = data["ValueSet"].get(valueset_id)

            # Unless we already have something in the VS:
            if not valueset:
                lg_id = unique_id(rdfID, form["Language_ID"])
                if lg_id in data["Variety"]:
                    src = None
                    if form["Source"]:
                        src = ",".join(form["Source"])
                    vs = data.add(
                        common.ValueSet,
                        valueset_id,
                        id=valueset_id,
                        language=data["Variety"][lg_id],
                        parameter=data["NumberParameter"][formpid],
                        contribution=contrib,
                        source=src,
                    )

            org_form = None
            # org forms only for numerals from channumerals
            if rdfID == 'numerals' and form["ID"] in org_forms:
                if unicodedata.normalize('NFC', org_forms[form["ID"]]["Form"].strip()) != form["Form"]:
                    org_form = org_forms[form["ID"]]["Form"]

            other_form = None
            if ds_dir in ds_metadata['other_form_map']:
                o_form_col = ds_metadata['other_form_map'][ds_dir]
                if o_form_col not in form:
                    if not other_form_warning:
                        args.log.warn('\nColumn "{0}" not found in form table!'.format(o_form_col))
                        other_form_warning = True
                else:
                    sep = ds["FormTable"].tableSchema.get_column(o_form_col).separator
                    if sep:
                        other_form = '{0} '.format(sep).join(form[o_form_col])
                    else:
                        other_form = form[o_form_col]

            DBSession.add(
                models.NumberLexeme(
                    id=unique_id(rdfID, form["ID"]),
                    name=form["Form"],
                    comment=form["Comment"],
                    is_loan=form["Loan"],
                    other_form=other_form,
                    org_form=org_form,
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
    for np in DBSession.query(models.NumberParameter, func.count(common.Parameter.pk)) \
            .join(common.Parameter) \
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
            .join(models.NumberParameter) \
            .filter(common.Parameter.pk == base_pk):
        np.count_of_datapoints = cnt_base
        break

    for prov in DBSession.query(models.Provider):
        q = DBSession.query(common.ValueSet.language_pk)\
            .filter(common.ValueSet.contribution_pk == prov.pk)\
            .distinct()
        prov.language_count = q.count()
        prov.update_jsondata(language_pks=[r[0] for r in q])

        prov.parameter_count = DBSession.query(common.ValueSet.parameter_pk) \
            .filter(common.ValueSet.contribution_pk == prov.pk) \
            .distinct() \
            .count()
        prov.lexeme_count = DBSession.query(common.Value.pk)\
            .join(common.ValueSet)\
            .filter(common.ValueSet.contribution_pk == prov.pk)\
            .count()

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

    args.log.info('Processing family trees')
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
