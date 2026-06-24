"""
Tests for the optional TwelveLabs backend.

The network-dependent tests are skipped automatically unless a
TWELVELABS_API_KEY is set in the environment, so the suite is safe to run
without credentials. The no-network test exercises the opt-in guard without
touching the API.

Run with:  pytest tests/test_twelvelabs_backend.py
"""

import os
import pytest

from storytoolkitai.core.toolkit_ops.twelvelabs_backend import TwelveLabsBackend

HAS_KEY = bool(os.environ.get('TWELVELABS_API_KEY'))
skip_no_key = pytest.mark.skipif(not HAS_KEY, reason='TWELVELABS_API_KEY not set')


def test_requires_api_key(monkeypatch):
    """Without a key (constructor, config or env), instantiation must fail - opt-in only."""
    monkeypatch.delenv('TWELVELABS_API_KEY', raising=False)
    with pytest.raises(ValueError):
        TwelveLabsBackend(api_key=None, stAI=None)


def test_explicit_key_does_not_require_env(monkeypatch):
    """An explicit api_key is accepted even when nothing is in the environment."""
    monkeypatch.delenv('TWELVELABS_API_KEY', raising=False)
    backend = TwelveLabsBackend(api_key='test-key')
    assert backend.api_key == 'test-key'
    # the SDK client must stay lazy - constructing the backend should not create it
    assert backend._client is None


@skip_no_key
def test_embed_text_returns_vector():
    """Marengo text embedding returns a non-empty float vector."""
    backend = TwelveLabsBackend(api_key=os.environ['TWELVELABS_API_KEY'])
    vector = backend.embed_text('a cat playing the piano')
    assert vector is not None
    assert len(vector) > 0
    assert all(isinstance(x, float) for x in vector[:5])


@skip_no_key
def test_list_indexes():
    """Listing indexes returns a list of (id, name) tuples (possibly empty)."""
    backend = TwelveLabsBackend(api_key=os.environ['TWELVELABS_API_KEY'])
    indexes = backend.list_indexes()
    assert indexes is not None
    for idx in indexes:
        assert len(idx) == 2
