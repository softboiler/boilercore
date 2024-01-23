"""Hash utilities."""

from collections.abc import Callable, Hashable
from inspect import getsource, signature
from typing import Any

from cachier.core import _default_hash_func


def hash_args_PATCHED(  # noqa: N802
    fun: Callable[..., Any], args: tuple[Any, ...], kwds: dict[str, Any]
) -> str:
    """Hash a particular set of arguments meant to be passed to a particular function.

    Passing this function, with `fun` applied via `partial`, to `cachier`'s `hash_func`
    decorator allows us to create a cacheable form of `fun`.

    Returns: Hash of the arguments.

    Args:
        fun: Function from which the signature will be generated.
        args: Positional arguments to hash.
        kwds: Keyword arguments to hash.

    Example:
        ```Python
        import cachier
        from functools import partial

        @cachier(hash_func=partial(hash_args_PATCHED, uncached_function))
        def cached_function(*args, *kwds):
            return uncached_function(*args, *kwds)
        ```
    """
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
    dict: lambda v: frozenset(
        {
            k: frozenset(v_.items()) if isinstance(v_, dict) else v
            for k, v_ in v.items()
        }.items()
    ),
    list: lambda v: frozenset(v),
}
"""Transforms to make values hashable."""
