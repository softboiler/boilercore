"""Tests for notebook namespaces."""

from types import SimpleNamespace

from boilercore_tests import NB


def test_not_cached_before(cache_file):
    """Notebook is not cached before."""
    assert not cache_file.exists()


def test_empty_ns(cached_function):
    """Namespace is empty."""
    assert cached_function() == SimpleNamespace()


def test_cached_equals(cached_function):
    """Cached function returns the same namespace."""
    assert cached_function() == cached_function()


def test_cached(cached_function, cache_file):
    """Cached function creates a cache file."""
    cached_function()
    assert cache_file.exists()


def test_cache_startswith(cached_function, cache_file):
    """Cache file starts with a certain byte string."""
    cached_function()
    assert cache_file.read_bytes().startswith(b"\x80\x04\x95\xc2")


def test_cleared(cached_function, cache_file):
    """Cache file is cleared."""
    cached_function()
    cached_function.clear_cache()
    assert cache_file.read_bytes() == b"\x80\x04\x7d\x94\x2e"


def test_only_a(cached_function):
    """Namespace has only attribute 'a'."""
    ns = cached_function(NB, {})
    ns.a  # noqa: B018
    assert all(attr == "a" for attr in ns.__dict__)


def test_a_equals(cached_function):
    """Namespace attribute 'a' is as expected."""
    ns = cached_function(NB, {})
    assert ns.a == 1
