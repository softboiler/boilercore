"""Types."""

from pathlib import Path
from typing import TypeAlias, TypeVar

T = TypeVar("T", bound=Path | str)
PathOrPaths: TypeAlias = T | list[T] | dict[str, T]
Paths: TypeAlias = dict[str, PathOrPaths[T]]
