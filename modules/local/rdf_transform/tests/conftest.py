"""Shared pytest fixtures: a `client` for the FastAPI app (with lifespan so
ontologies load), the path to `examples/`, and a `requires_morph` marker that
skips tests needing the Morph-KGC engine (which requires Python >= 3.10)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def client():
    # `with TestClient(app)` triggers FastAPI lifespan startup/shutdown
    # so `app.state.ontologies` is populated for /validate and /.
    with TestClient(app) as c:
        yield c


def _morph_available() -> bool:
    # morph-kgc imports cleanly only on Python >= 3.10 (uses `X | Y` syntax),
    # so attempt the real import rather than just locating the spec.
    try:
        import morph_kgc  # noqa: F401
    except Exception:
        return False
    return True


requires_morph = pytest.mark.skipif(
    not _morph_available(),
    reason="Requires morph-kgc (Python >= 3.10)",
)
