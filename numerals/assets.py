from clld.web.assets import environment
from clldutils.path import Path

import numerals


environment.append_path(
    Path(numerals.__file__).parent.joinpath('static').as_posix(),
    url='/numerals:static/')
environment.load_path = list(reversed(environment.load_path))
