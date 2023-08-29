"""Paths and modules."""

from collections.abc import Iterable
from pathlib import Path
from re import compile
from types import ModuleType


def get_package_dir(package: ModuleType) -> Path:
    return Path(next(iter(package.__path__)))


def map_stages(stages_dir: Path, package_dir: Path) -> dict[str, Path]:
    """Map stage module names to their paths."""
    stages: dict[str, Path] = {}
    for path in walk_module_paths(stages_dir, package_dir, glob="[!__]*.[py ipynb]*"):
        module = get_module_rel(get_module(path, package_dir), stages_dir.name)
        stages[module.replace(".", "_")] = path
    return stages


def walk_module_paths(
    package: Path, top: Path, suffix: str = ".py", glob: str | None = None
) -> Iterable[Path]:
    """Walk modules from a given submodule path and the top level library directory."""
    for directory in (
        package,
        *[
            path
            for path in package.iterdir()
            if path.is_dir() and "__" not in str(path.relative_to(top.parent))
        ],
    ):
        yield from sorted(directory.glob(glob or f"[!__]*{suffix}"))


def get_module(module: Path, package: Path) -> str:
    """Get module name given the submodule path and the top level library directory."""
    return (
        str(module.relative_to(package.parent).with_suffix(""))
        .replace("\\", ".")
        .replace("/", ".")
    )


def walk_modules(package: Path, top: Path, suffix: str = ".py") -> Iterable[str]:
    """Walk modules from a given submodule path and the top level library directory."""
    for module in walk_module_paths(package, top, suffix):
        yield get_module(module, top)


def get_module_rel(module: str, relative: str) -> str:
    """Get module name relative to another module."""
    return compile(rf".*{relative}\.").sub(repl="", string=module)
