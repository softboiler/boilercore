"""Hash utilities."""

from collections.abc import Callable, Hashable
from inspect import getsource, signature
from typing import Any

from cachier.core import _default_hash_func


def hash_args(
    fun: Callable[..., Any], args: tuple[Any, ...], kwds: dict[str, Any]
) -> str:
    """Hash function arguments."""
    bound_args = signature(fun).bind(*args, **kwds).arguments
    return _default_hash_func(
        (), {param: make_hashable(val) for param, val in bound_args.items()}
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


TRANSFORMS = {
    Callable: lambda v: getsource(v),
    dict: lambda v: frozenset(v.items()),
    list: lambda v: frozenset(v),
}
"""Transforms to make values hashable."""
