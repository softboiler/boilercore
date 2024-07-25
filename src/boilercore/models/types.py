"""Types."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeAlias, TypeVar

T = TypeVar("T", bound=Path | str)
PathOrPaths: TypeAlias = T | Sequence[T] | Mapping[str, T]
Paths: TypeAlias = Mapping[str, PathOrPaths[T]]
