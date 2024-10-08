from setuptools import setup, find_packages

setup(
    name='numerals',
    version='0.0',
    description='numerals',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'attrs>=23.1',
        'clld>=11.2.2',
        'clldmpg>=4.3.1',
        'clld-glottologfamily-plugin>=4.1.0',
        'clld-phylogeny-plugin>=1.6.0',
        'clld-cognacy-plugin>=0.3.0',
        'csvw>=3.3.0',
        'pybtex>=0.24',
        'pycldf>=1.38.1',
        'sqlalchemy>=1.4.46',
        'waitress',
    ],
    extras_require={
        'dev': [
            'flake8',
            'pyramid_debugtoolbar',
            'psycopg2',
            'tox',
        ],
        'test': [
            'mock',
            'pytest>=6.2.5',
            'pytest-clld>=1.1.0',
            'pytest-mock>=3.6.1',
            'pytest-cov>=2.12.1',
            'coverage>=5.5',
            'selenium',
            'zope.component>=3.11.0',
        ],
    },
    test_suite="numerals",
    entry_points="""\
    [paste.app_factory]
    main = numerals:main
""")
