import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ('get_html', '/'),
    ])
def test_pages(app, method, path):
    getattr(app, method)(path)
