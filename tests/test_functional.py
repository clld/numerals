import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ('get_html', '/'),
        ('get_html', '/contributions'),
        ('get_html', '/contributions/numerals.md.html'),
        ('get_html', '/contributions/numerals'),
        ('get_html', '/parameters/-1'),
        ('get_html', '/parameters/1'),
        ('get_html', '/valuesets/10-numerals-rapa1244-1'),
        ('get_html', '/valuesets/1-numerals-chan1310-1'),
        ('get_html', '/values?contribution=numerals&sSearch_0=Base'),
        ('get_html', '/sources'),
        ('get_html', '/parameters/-1.geojson?domainelement=decimal&layer=decimal'),
        ('get_html', '/languages'),
        ('get_html', '/languages/numerals-chan1310-1'),
        ('get_html', '/languages/numerals-aton1241-1'),
        ('get_html', '/languages/numerals-abai1240-1'),
        ('get_html', '/languages/numerals-abai1240-1.snippet.html'),
        ('get_html', '/languages/numerals-abai1240-1.snippet.html?map_pop_up=1&map_pop_up=1'),
        ('get_html', '/phylogenies/ainu?parameters=10'),
    ])
def test_pages(app, method, path):
    getattr(app, method)(path)
