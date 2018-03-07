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
        'clld>=4.1.2',
        'clldmpg>=3.1.1',
        'clld-glottologfamily-plugin',
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
