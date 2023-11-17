"""Hash utilities."""

from collections.abc import Callable, Hashable
from inspect import getsource, signature
from typing import Any

from cachier.core import _default_hash_func

TRANSFORMS = {
    Callable: lambda v: getsource(v),
    dict: lambda v: frozenset(v.items()),
    list: lambda v: frozenset(v),
}
"""Transforms to make values hashable."""


def hash_args(
    function: Callable[..., Any], args: tuple[Any, ...], kwds: dict[str, Any]
) -> str:
    """Hash function arguments."""
    defaults = {p: v.default for p, v in signature(function).parameters.items()}
    kwds_from_args = dict(zip(defaults.keys(), args, strict=False))
    return _default_hash_func(
        (), {p: make_hashable(v) for p, v in (defaults | kwds | kwds_from_args).items()}
    )


def make_hashable(value: Any) -> Hashable:
    """Make value hashable."""
    if isinstance(value, Hashable):
        return value
    for typ, transform in TRANSFORMS.items():
        if isinstance(value, typ):
            return transform(value)
    raise TypeError(
        f"Value of type {type(value)} not hashable and transform not implemented."
    )
