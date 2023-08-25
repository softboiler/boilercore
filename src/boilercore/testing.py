"""Helper functions for testing boiler code."""

import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from re import compile

from nbqa.__main__ import _get_nb_to_tmp_mapping, _save_code_sources  # type: ignore


def make_tmp_project_with_nb_stages(stages: list[Path]) -> Callable[[Path], None]:
    """Fixture factory for temp project with notebook stages."""

    def _tmp_project_with_nb_stages(tmp_project: Path):
        """Enable import of notebook stages like `importlib.import_module("stage")`."""
        # For importing tmp_project stages in tests
        sys.path.insert(0, str(tmp_project))
        for nb in stages:
            (tmp_project / nb.with_suffix(".py").name).write_text(
                encoding="utf-8", data=get_nb_content(nb)
            )

    return _tmp_project_with_nb_stages


def get_nb_content(nb: Path) -> str:
    """Get the contents of a notebook."""
    _, (newlinesbefore, _) = _save_code_sources(
        _get_nb_to_tmp_mapping(
            [str(nb)],
            None,
            None,
            False,
        ),
        [],
        [],
        False,
        "abc",
    )
    script = next(Path(script) for script in list(newlinesbefore.keys()))
    contents = script.read_text(encoding="utf-8")
    script.unlink()
    return contents


def walk_modules(package: Path, top: Path) -> Iterable[str]:
    """Walk modules from a given submodule path and the top level library directory."""
    for directory in (
        package,
        *[
            path
            for path in package.iterdir()
            if path.is_dir() and "__" not in str(path.relative_to(top.parent))
        ],
    ):
        for example in sorted(directory.glob("[!__]*.py")):
            yield (get_module(example, top))


def get_module(submodule: Path, library: Path) -> str:
    """Get module name given the submodule path and the top level library directory."""
    return (
        str(submodule.relative_to(library.parent).with_suffix(""))
        .replace("\\", ".")
        .replace("/", ".")
    )


def get_module_rel(module: str, relative: str) -> str:
    """Get module name relative to another module."""
    return compile(rf".*{relative}\.").sub(repl="", string=module)
