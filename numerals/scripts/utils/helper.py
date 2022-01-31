import git
import subprocess
from clldutils import jsonlib
from clldutils.path import Path
from clldutils.misc import slug
from numerals.scripts.utils.cldf_zenodo import download_from_doi


def prepare_additional_datasets(args, submissions_path, cache_dir):
    # download and prepare resp. additional datasets
    other_form_map = {}
    lang_contributor_map = {}
    lang_comment_map = {}
    missing_metadata = {}
    rdfids = {}
    contrib_paths_map = {}
    contrib_repos = {}
    contrib_dois = {}
    contrib_skips = []
    contrib_swaps = []
    unique_sids = set()
    for contrib_dir in submissions_path.iterdir():
        if not contrib_dir.is_dir():
            continue

        args.log.info('Loading submission {0}'.format(contrib_dir.name))
        contrib_md = jsonlib.load(contrib_dir / 'md.json')
        sid = contrib_md['id']
        if sid in unique_sids:
            args.log.error('Id "{0}" of {1} is already used'.format(sid, contrib_dir.name))
            assert False, 'id error'

        rdfids[sid] = sid

        if contrib_md.get('skip') and contrib_md['skip']:
            contrib_skips.append(sid)
            args.log.info('   will be skipped')
            continue

        if contrib_md.get('doi'):
            doi = contrib_md['doi']
            contrib_dois[sid] = doi
            path = cache_dir / '{}-{}'.format(sid, slug(doi))
            if not path.exists():
                args.log.info(' * downloading dataset from Zenodo; doi: {0}'.format(doi))
                download_from_doi(doi, path)
            else:
                args.log.info('   using cache')
            # get the first directory name as contrib_path for initdb
            for child in path.iterdir():
                if child.is_dir():
                    contrib_paths_map[str(child.name)] = sid
                    break

        elif contrib_md.get('repo'):
            repo = contrib_md.get('repo')
            contrib_repos[sid] = repo
            # latest commit on the default branch
            path = cache_dir / sid
            if not path.exists():
                args.log.info(' * cloning {0} into {1}'.format(repo, path))
                git.Git().clone(repo, path)
            else:
                args.log.info(' * pulling latest commit')
                git.Git(str(path)).pull()
            contrib_paths_map[sid] = sid

        else:
            path = cache_dir / sid

        if not path.exists():
            args.log.error('could not find folder', str(path))
            continue

        if contrib_md.get('other_form'):
            other_form_map[sid] = contrib_md['other_form']
            if contrib_md.get('swap_forms') and contrib_md['swap_forms']:
                contrib_swaps.append(sid)

        if contrib_md.get('LanguageContributor'):
            lang_contributor_map[sid] = contrib_md['LanguageContributor']

        if contrib_md.get('LanguageComment'):
            lang_comment_map[sid] = contrib_md['LanguageComment']

        if contrib_md.get('missing_metadata'):
            missing_metadata[sid] = contrib_md['missing_metadata']

    return {
        'other_form_map': other_form_map,
        'rdfids': rdfids,
        'contrib_paths_map': contrib_paths_map,
        'contrib_repos': contrib_repos,
        'contrib_dois': contrib_dois,
        'contrib_skips': contrib_skips,
        'contrib_swaps': contrib_swaps,
        'lang_contributor_map': lang_contributor_map,
        'lang_comment_map': lang_comment_map,
        'missing_metadata': missing_metadata
    }


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
