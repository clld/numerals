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
        'attrs>=22.2',
        'clld>=10',
        'clldmpg>=4.3.0',
        'clld-glottologfamily-plugin>=4.0.0',
        'clld-phylogeny-plugin>=1.5',
        'clld-cognacy-plugin>=0.2.1',
        'csvw>=1.11.0',
        'pybtex>=0.24',
        'pycldf>=1.23.0',
        'sqlalchemy>=1.4.27',
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
