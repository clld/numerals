# FIXME remove this entire module, once the actual cldf-zenodo package is
# published

import io
import re
import json
import pathlib
import zipfile
import urllib.request

from bs4 import BeautifulSoup as bs
import requests


def download_from_doi(doi, outdir=pathlib.Path('.')):
    res = requests.get('https://doi.org/{0}'.format(doi))
    assert re.search('zenodo.org/record/[0-9]+$', res.url)
    res = requests.get(res.url + '/export/json')
    soup = bs(res.text, 'html.parser')
    res = json.loads(soup.find('pre').text)
    for f in res['files']:
        if f['type'] == 'zip':
            r = requests.get(f['links']['self'], stream=True)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(str(outdir))
        elif f['type'] == 'tar':
            # what about a tar in there?
            raise NotImplementedError()
        elif f['type'] == 'gz':
            raise NotImplementedError()
        else:
            urllib.request.urlretrieve(
                f['links']['self'],
                outdir / f['links']['self'].split('/')[-1],
            )
    sub_dirs = [f for f in outdir.iterdir() if f.is_dir()]
    assert (outdir / sub_dirs[0] / 'cldf').is_dir(), 'no cldf directory found'
    return outdir
