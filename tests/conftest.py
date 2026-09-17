"""Shared pytest configuration."""

import pytest


@pytest.fixture(autouse=True, scope="session")
def _never_open_a_browser():
    """No test may open a browser tab, whatever it passes for display.

    Plotly's ``fig.show()`` outside a notebook does not draw anything locally:
    it starts an ephemeral HTTP server on 127.0.0.1, points the default
    browser at it, and blocks until that one request arrives. A test run that
    opens tabs is a test run nobody can leave unattended.

    Installed in EVERY repo rather than only where a scan found display calls.
    Going by scan is what let the tabs come back twice: a regex missed six
    repos because it could not cross a line end, and the AST scan that
    replaced it still only sees a display keyword passed as a literal ``True``
    -- one passed positionally, through a variable or from a parametrize list
    is invisible to both. The fixture is inert where nothing displays, so
    predicting which repos need it buys nothing and costs a recurrence.

    The branch under test still executes and still counts as covered; it just
    cannot reach a browser. This is the half the housekeeper's Rule 14 audits
    cannot see -- they read library ``src/``, and this lives in ``tests/``.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        yield
        return

    original = go.Figure.show
    go.Figure.show = lambda self, *args, **kwargs: None
    try:
        yield
    finally:
        go.Figure.show = original
