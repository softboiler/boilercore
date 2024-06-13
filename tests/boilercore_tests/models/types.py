"""Types."""

from pathlib import Path
from typing import TypeAlias

VarietyOfPaths: TypeAlias = tuple[Path, tuple[Path, ...], dict[str, Path], Path]
