"""Paths and modules."""

from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from re import compile
from shlex import quote
from types import ModuleType

from dulwich.porcelain import status, submodule_list
from dulwich.repo import Repo


def get_package_dir(package: ModuleType) -> Path:
    return Path(next(iter(package.__path__)))


def map_stages(stages_dir: Path, package_dir: Path) -> dict[str, Path]:
    """Map stage module names to their paths."""
    stages: dict[str, Path] = {}
    for path in walk_module_paths(stages_dir, package_dir, glob="[!__]*.[py ipynb]*"):
        module = get_module_rel(get_module(path, package_dir), stages_dir.name)
        stages[module.replace(".", "_")] = path
    return stages


def walk_modules(package: Path, top: Path, suffix: str = ".py") -> Iterable[str]:
    """Walk modules from a given submodule path and the top level library directory."""
    for module in walk_module_paths(package, top, suffix):
        yield get_module(module, top)


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


def get_module_rel(module: str, relative: str) -> str:
    """Get module name relative to another module."""
    return compile(rf".*{relative}\.").sub(repl="", string=module)


def fold(path: Path) -> str:
    """Resolve and normalize a path to a POSIX string path with forward slashes."""
    return quote(str(path.resolve()).replace("\\", "/"))


def modified(nb: str) -> bool:
    """Check whether notebook is modified."""
    return Path(nb) in (change.resolve() for change in get_changes())


def get_changes() -> list[Path]:
    """Get pending changes."""
    staged, unstaged, _ = status(untracked_files="no")
    changes = {
        # Many dulwich functions return bytes for legacy reasons
        Path(path.decode("utf-8")) if isinstance(path, bytes) else path
        for change in (*staged.values(), unstaged)
        for path in change
    }
    # Exclude submodules from the changeset (submodules are considered always changed)
    return sorted(
        change
        for change in changes
        if change not in {submodule.path for submodule in get_submodules()}
    )


@dataclass
class Submodule:
    """Represents a git submodule."""

    _path: str | bytes
    """Submodule path as reported by the submodule source."""
    commit: str
    """Commit hash currently tracked by the submodule."""
    path: Path = Path()
    """Submodule path."""
    name: str = ""
    """Submodule name."""

    def __post_init__(self):
        """Handle byte strings reported by some submodule sources, like dulwich."""
        # Many dulwich functions return bytes for legacy reasons
        self.path = Path(
            self._path.decode("utf-8") if isinstance(self._path, bytes) else self._path
        )
        self.name = self.path.name


def get_submodules() -> list[Submodule]:
    """Get the special template and typings submodules, as well as the rest."""
    with closing(repo := Repo(str(Path.cwd()))):
        return [Submodule(*item) for item in list(submodule_list(repo))]
