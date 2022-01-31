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

try:
    import pylexibank
except ImportError:
    pylexibank = None

try:
    from pyconcepticon import Concepticon
except ImportError:
    Concepticon = None

import numerals
from numerals import models
from numerals.scripts.global_tree import tree
from numerals.scripts.utils.helper import unique_id, git_last_commit_date, prepare_additional_datasets


NUMERALS_RDFID = 'numerals'


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

    # add all other additional datasets and ignore datasets marked as 'skip'
    is_numerals_ds_found = False
    for ds in pycldf.iter_datasets(cache_dir):
        if str(ds.directory).endswith('/cldf'):
            ds_dir = ds_metadata['contrib_paths_map'].get(ds.directory.parent.name, ds.directory.parent.name)
            if ds_dir in ds_metadata['contrib_skips']:
                if ds_metadata['contrib_skips'][ds_dir]:
                    args.log.info('{0} will be skipped'.format(ds_dir))
                    continue
            if ds_dir == NUMERALS_RDFID:
                is_numerals_ds_found = True
            if 'missing_metadata' in ds_metadata and ds_dir in ds_metadata['missing_metadata']:
                for k, v in ds_metadata['missing_metadata'][ds_dir].items():
                    ds.properties[k] = v
            numeral_datasets.append(ds)

    assert is_numerals_ds_found, 'dataset "numerals" must be imported'

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
        published=date(2020, 11, 1),
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
        accessURL = ds.properties.get('dcat:accessURL', None)
        if ds_dir in ds_metadata['contrib_dois']:
            doi = ds_metadata['contrib_dois'][ds_dir]
            accessURL = 'https://doi.org/{0}'.format(doi)
        else:
            git_version = git_last_commit_date(ds.directory.parent)

        if accessURL is None:
            accessURL = ds_metadata['contrib_repos'][ds_dir]

        title = ds.properties.get('dc:title')
        description = ds.properties.get('dc:description', "")
        if description:
            title = '{} – {}'.format(title, description)

        contrib = models.Provider(
            id=rdfID,
            name=title,
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

        ns = ds.column_names

        param_map = {}
        for parameter in ds["ParameterTable"]:
            if ns.parameters.concepticonReference not in parameter\
                    or parameter[ns.parameters.concepticonReference] not in number_concept_map:
                continue

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

        lgs_with_no_data = set()
        for lg, forms in itertools.groupby(
                sorted(ds["FormTable"], key=lambda k: k[ns.forms.languageReference]),
                lambda x: x[ns.forms.languageReference]):
            if not any([f for f in forms if f[ns.forms.parameterReference] in param_map]):
                lgs_with_no_data.add(lg)

        if lgs_with_no_data:
            args.log.info('No data for {}'.format(', '.join(sorted(lgs_with_no_data))))

        ns_languages_contributor = "Contributor"
        if ns.languages.contributor is not None:
            ns_languages_contributor = ns.languages.contributor
        elif "lang_contributor_map" in ds_metadata and ds_dir in ds_metadata["lang_contributor_map"]:
            ns_languages_contributor = ds_metadata["lang_contributor_map"][ds_dir]

        ns_languages_comment = "Comment"
        if ns.languages.comment is not None:
            ns_languages_comment = ns.languages.comment
        elif "lang_comment_map" in ds_metadata and ds_dir in ds_metadata["lang_comment_map"]:
            ns_languages_comment = ds_metadata["lang_comment_map"][ds_dir]

        try:
            sep = ds["LanguageTable"].tableSchema.get_column(ns_languages_contributor).separator
        except AttributeError:
            sep = ""

        for language in ds["LanguageTable"]:
            if language[ns.languages.id] in lgs_with_no_data:
                continue

            if ns_languages_contributor in language:
                if sep:
                    creator = '{0} '.format(sep).join(language[ns_languages_contributor])
                else:
                    creator = language[ns_languages_contributor]
            else:
                creator = None

            # make language IDs unique cross datasets
            lg_id = unique_id(rdfID, language[ns.languages.id])
            if lg_id not in data["Variety"]:
                lang = data.add(
                    models.Variety,
                    lg_id,
                    id=lg_id,
                    name=language[ns.languages.name],
                    latitude=language[ns.languages.latitude],
                    longitude=language[ns.languages.longitude],
                    contrib_name=rdfID,
                    creator=creator,
                    comment=language.get(ns_languages_comment, None),
                    url_soure_name=language.get("SourceFile", None),
                )
                if language[ns.languages.glottocode]:
                    load_family_langs.append((language[ns.languages.glottocode], lang))
                if language[ns.languages.iso639P3code]:
                    add_language_codes(data, lang, language[ns.languages.iso639P3code])
            else:
                args.log.warn("Language ID '{0}' already exists".format(lg_id))

        # Add Base info if given and 'org_form' for 'numerals' only
        org_forms = {}
        if rdfID == NUMERALS_RDFID:
            org_forms = {f["ID"]: f for f in numeral_datasets[0]}
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
                        contribution=contrib,
                    )

                    common.Value(
                        id=data["Variety"][lg_id].id,
                        valueset=vs,
                        domainelement=de
                    )

        DBSession.flush()

        other_form_warning = False
        add_other_form = bool(ds_dir in ds_metadata['other_form_map'])
        swap_forms = bool(ds_dir in ds_metadata['contrib_swaps'])
        for form in pylexibank.progressbar(ds["FormTable"], desc="reading {0}".format(rdfID)):

            if form[ns.forms.languageReference] in lgs_with_no_data\
                    or form[ns.forms.parameterReference] not in param_map:
                continue

            formpid = param_map[form[ns.forms.parameterReference]]

            valueset_id = "{0}-{1}-{2}".format(formpid, rdfID, form[ns.forms.languageReference])
            valueset = data["ValueSet"].get(valueset_id)

            # Unless we already have something in the VS:
            if not valueset:
                lg_id = unique_id(rdfID, form[ns.forms.languageReference])
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
                        contribution=contrib,
                        source=src,
                    )

            org_form = None
            # org forms only for numerals from channumerals
            if rdfID == NUMERALS_RDFID and form["ID"] in org_forms:
                if unicodedata.normalize('NFC', org_forms[form["ID"]]["Form"].strip()) != form["Form"]:
                    org_form = org_forms[form["ID"]]["Form"]

            form_ = form[ns.forms.form]
            other_form = None
            if add_other_form:
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
                    if swap_forms and other_form:
                        form_, other_form = other_form, form_

            DBSession.add(
                models.NumberLexeme(
                    id=unique_id(rdfID, form[ns.forms.id]),
                    name=form_,
                    comment=form[ns.forms.comment],
                    is_loan=form["Loan"] if "Loan" in form else None,
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
        if prov.id == 'numerals':
            # do not count 'base'
            pcnt -= 1
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
