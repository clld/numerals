import unicodedata
import pylexibank
import subprocess
import re
from pyconcepticon import Concepticon
from clldutils.path import Path
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import collkey, with_collkey_ddl
from clld.lib.bibtex import Database
from clldutils import color
from clldutils.misc import slug
from clldutils.path import git_describe
from clld.cliutil import Data, add_language_codes, bibtex2source
from clld_glottologfamily_plugin.util import load_families
from clld_glottologfamily_plugin.models import Family
from clld_phylogeny_plugin.models import Phylogeny, LanguageTreeLabel, TreeLabel
from pycldf.dataset import iter_datasets
from six import text_type
from sqlalchemy import func, Index
from datetime import date
import json
import ete3

import numerals
from numerals import models
from numerals.scripts.global_tree import tree


with_collkey_ddl()


def main(args):

    def unique_id(ds_id, local_id):
        return '{0}-{1}'.format(ds_id, local_id)

    def git_last_commit_date(dir_, git_command='git'):
        dir_ = Path(dir_)
        if not dir_.exists():
            raise ValueError('cannot read from non-existent directory')
        dir_ = dir_.resolve()
        cmd = [
            git_command,
            '--git-dir={0}'.format(dir_.joinpath('.git')),
            '--no-pager', 'log', '-1', '--format="%ai"'
        ]
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode == 0:
                res = stdout.strip()  # pragma: no cover
            else:
                raise ValueError(stderr)
        except (ValueError, FileNotFoundError):
            return ''
        if not isinstance(res, str):
            res = res.decode('utf8')
        return res.replace('"', '')

    assert args.glottolog, 'The --glottolog option is required!'
    assert args.concepticon, 'The --concepticon option is required!'

    data_set_path = input('Path to Numerals cldf datasets:') or\
        Path(numerals.__file__).parent.parent.parent.parent / 'numeralbank'

    numeral_datasets, main_numeral_found, org_numeral_found = [], False, False
    for ds in iter_datasets(data_set_path):
        try:
            if str(ds.directory).endswith('/cldf'):
                if ds.properties.get('rdf:ID', '') == 'channumerals':
                    # general Numeral dataset must be first item
                    numeral_datasets.insert(0, ds)
                    org_numeral_found = True
                else:
                    numeral_datasets.append(ds)
                    if ds.properties.get('rdf:ID', '') == 'numerals':
                        main_numeral_found = True
        except IndexError:
            continue

    assert main_numeral_found, 'No main Numeral dataset found'
    assert org_numeral_found, 'No original Chan Numeral dataset found'
    assert numeral_datasets, 'No valid Numeral datasets found'

    # first ds must be Chan's original dataset, second ds must be the main numerals one
    for idx, ds in enumerate(numeral_datasets):
        if ds.properties.get('rdf:ID', '') == 'numerals':
            numeral_datasets.insert(1, numeral_datasets.pop(idx))
            break

    # get all concepts of numerals and them to integer ids
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
    for i, ds in enumerate(numeral_datasets[1:]):

        rdfID = ds.properties.get('rdf:ID')

        accessURL = ds.properties.get('dcat:accessURL')
        m = re.findall(r'^(.*?)\-', git_describe(ds.directory.parent))
        if m:
            git_version = m[0]
            accessURL = '{0}/releases/tag/{1}'.format(accessURL, git_version)
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
            org_forms = {f["ID"]: f for f in numeral_datasets[0]["FormTable"]}

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

            org_form = ""
            # org forms only for numerals from channumerals
            f_id = unique_id(rdfID, form["ID"])
            if rdfID == 'numerals' and form["ID"] in org_forms:
                if unicodedata.normalize('NFC', org_forms[form["ID"]]["Form"].strip()) != form["Form"]:
                    org_form = org_forms[form["ID"]]["Form"]

            other_form = form["Other_Form"] if "Other_Form" in form else None
            # handle specific datasets' other forms
            if rdfID == 'ids':
                other_form = '; '.join(form["AlternativeValues"]) if "AlternativeValues" in form else None
            elif rdfID == 'northeuralex':
                other_form = form["Value"] or None

            DBSession.add(
                models.NumberLexeme(
                    id=f_id,
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
