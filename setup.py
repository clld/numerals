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
        'attrs>=19.2',
        'clld>=6.0.1',
        'clldmpg>=3.4.0',
        'clld-glottologfamily-plugin>=3.1.0',
        'clld-phylogeny-plugin>=1.4.0',
        'clld-cognacy-plugin>=0.2.0',
        'csvw>=1.5.6',
        'pybtex>=0.22',
        'pycldf>=1.6.4',
        'sqlalchemy',
        'waitress',
    ],
    extras_require={
        'dev': [
            'flake8',
            'psycopg2',
            'tox',
        ],
        'test': [
            'mock',
            'pytest>=3.1',
            'pytest-clld>=0.4',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
            'selenium',
            'zope.component>=3.11.0',
        ],
    },
    test_suite="numerals",
    entry_points="""\
    [paste.app_factory]
    main = numerals:main
""")
