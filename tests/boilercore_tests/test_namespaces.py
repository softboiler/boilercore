"""Tests for notebook namespaces."""

from types import SimpleNamespace

from boilercore_tests import NB


def test_not_cached_before(cache_file):
    assert not cache_file.exists()


def test_empty_ns(cached_function):
    assert cached_function() == SimpleNamespace()


def test_cached_equals(cached_function):
    assert cached_function() == cached_function()


def test_cached(cached_function, cache_file):
    cached_function()
    assert cache_file.exists()


def test_cache_startswith(cached_function, cache_file):
    cached_function()
    assert cache_file.read_bytes().startswith(b"\x80\x04\x95\xc2")


def test_cleared(cached_function, cache_file):
    cached_function()
    cached_function.clear_cache()
    assert cache_file.read_bytes() == b"\x80\x04\x7d\x94\x2e"


def test_only_a(cached_function):
    ns = cached_function(NB, {})
    ns.a  # noqa: B018
    assert all(attr in ["a"] for attr in ns.__dict__)


def test_a_equals(cached_function):
    ns = cached_function(NB, {})
    assert ns.a == 1
