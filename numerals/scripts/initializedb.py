from __future__ import unicode_literals

import re
import string
import sys
import unicodedata
from itertools import groupby

import xlrd
from clld.db.meta import DBSession
from clld.db.models import common
from clld.scripts.util import initializedb, Data
from clld_glottologfamily_plugin.util import load_families
from clldutils.misc import slug

import numerals
from numerals import models


def main(args):
    data = Data()

    dataset = common.Dataset(
        id=numerals.__name__,
        name="Numeralbank",
        publisher_name="Max Planck Institute for the Science of Human History",
        publisher_place="Jena",
        publisher_url="http://www.shh.mpg.de",
        license="http://creativecommons.org/licenses/by/4.0/",
        domain='numerals.clld.org',
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name':
                'Creative Commons Attribution 4.0 International License'})

    DBSession.add(dataset)

    for i, (id_, name) in enumerate([
        ('verkerkannemarie', 'Annemarie Verkerk'),
        ('rzymskichristoph', 'Christoph Rzymski'),
    ]):
        ed = data.add(common.Contributor, id_, id=id_, name=name)
        common.Editor(dataset=dataset, contributor=ed, ord=i + 1)

    DBSession.add(dataset)

    contrib = data.add(common.Contribution, 'numerals', id='numerals',
                       name='Eugene Chan\'s numerals')

    header = [
        'name', 'country', 'iso', 'glotto_name', 'glotto_code', 'lg_link',
        'audio', 'source', 'nr_sets', 'variant'
    ]

    meta = {}

    for row in iter_sheet_rows('META', args.data_file('numeral_301216.xlsx')):
        row = dict(zip(header, row))
        meta[(row['lg_link'], row['variant'])] = row

    for key, items in groupby(
            sorted(iter_sheet_rows('NUMERAL',
                                   args.data_file('numeral_301216.xlsx')),
                   key=lambda r: (str(r[2]), str(r[3]), str(r[0]))),
            lambda r: (r[2], int(r[3] or 1))):
        if key not in meta:
            continue

        lid = '{0}-{1}'.format(*key)
        md = meta[key]

        if md['lg_link'] == 'DangauraTharu.htm':
            continue
        elif md['lg_link'] == 'LowSaxon-Twente.htm':
            continue
        elif md['lg_link'] == 'LowSaxon.htm':
            continue

        data.add(models.Variety, lid, id=my_slug(lid), name=md['name'],
                 description=md['glotto_code'])
        # source, ref = sources.get(md['source']), None
        # if source:
        #     ds.add_sources(source)
        #     ref = source.id
        for concept, rows in groupby(items, lambda x: x[0]):
            parameter = data['Parameter'].get(concept)

            if not parameter:
                parameter = data.add(
                    common.Parameter,
                    concept,
                    id=slug(str(concept)),
                    name=concept,
                )

            vs_id = data['Variety'][lid].id + '-' + parameter.id

            vs = data.add(
                common.ValueSet,
                vs_id,
                id=vs_id,
                language=data['Variety'][lid],
                parameter=parameter,
                contribution=contrib,
                # Comment=row[4] or None,
            )

            for k, row in enumerate(rows):
                if row[1]:
                    common.Value(id=vs_id + '-' + str(k), name=row[1],
                                 valueset=vs)

    load_families(
        Data(), [(l.description, l) for l in DBSession.query(common.Language)],
        strict=False
    )


def iter_sheet_rows(sname, fname):
    wb = xlrd.open_workbook(fname.as_posix())
    sheet = wb.sheet_by_name(sname)

    for i in range(sheet.nrows):
        if i > 0:
            yield [col.value for col in sheet.row(i)]


def my_slug(s, remove_whitespace=True, lowercase=True):
    res = ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')
    if lowercase:
        res = res.lower()
    for c in string.punctuation:
        if c == '-':
            continue
        else:
            res = res.replace(c, '')
    res = re.sub('\s+', '' if remove_whitespace else ' ', res)
    res = res.encode('ascii', 'ignore').decode('ascii')
    return res


# noinspection PyUnusedLocal
def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """


if __name__ == '__main__':  # pragma: no cover
    initializedb(create=main, prime_cache=prime_cache)
    sys.exit(0)
