# coding: utf8
from __future__ import unicode_literals, print_function, division

from numerals.scripts.initializedb import main, prime_cache


def test_dbinit(db):
    main(None)
    prime_cache(None)
