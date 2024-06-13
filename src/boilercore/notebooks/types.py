"""Types."""

from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeAlias

Params: TypeAlias = Mapping[str, Any]
Attributes: TypeAlias = Iterable[str]

SimpleNamespaceReceiver: TypeAlias = Callable[..., Any]
"""Should be a `Callable` with an `ns` parameter expecting a `SimpleNamespace`."""
