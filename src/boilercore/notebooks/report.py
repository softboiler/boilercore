"""Generate reports for notebooks tracked by DVC."""

from asyncio import TaskGroup
from collections.abc import Callable, Coroutine
from concurrent.futures import ProcessPoolExecutor
from contextlib import AbstractContextManager
from functools import wraps
from os import chdir
from pathlib import Path
from shlex import split
from sys import stdout
from tempfile import NamedTemporaryFile
from typing import Any
from urllib import request

from dulwich.porcelain import add
from dvc.repo import Repo
from loguru import logger
from ploomber_engine import execute_notebook

from boilercore import notebooks
from boilercore.paths import fold

logger.remove()
logger.add(
    sink=stdout, enqueue=True, format=("<green>{time:mm:ss}</green> | {message}")
)
logger = logger.opt(colors=True)

ZOTERO = Path(NamedTemporaryFile().name)
"""Temporary file path which will contain the Zotero Lua filter.

Usage conforms to [MIT license][#license] of `retorquere/zotero-better-bibtex`.

[#license]: <https://raw.githubusercontent.com/retorquere/zotero-better-bibtex/v6.7.164/LICENSE>
"""
ZOTERO.write_bytes(
    request.urlopen(
        "https://raw.githubusercontent.com/retorquere/zotero-better-bibtex/v6.7.164/site/content/exporting/zotero.lua"
    ).read()
)


async def generate(paths, repo: Repo | None = None):
    """Generate reports for notebooks."""
    nbs = get_nbs(repo, paths)
    if not nbs:
        return
    await log(clean(nbs))
    nbs = get_nbs(repo, paths)
    if not nbs:
        return
    await log(execute(nbs, paths))
    await log(export(nbs, paths))
    await log(report(nbs, paths))
    commit(repo, paths)


async def log(coroutine):
    """Log the start and end of a coroutine."""
    logger.info(f"<yellow>START</yellow> {coroutine.__name__}")
    await coroutine
    logger.info(f"<green>FINISH</green> {coroutine.__name__}")


# * -------------------------------------------------------------------------------- * #
# * NOTEBOOK PROCESSING


def get_nbs(repo: Repo | None, paths) -> list[str]:
    """Get all notebooks or just the modified ones."""
    return (
        fold_modified_nbs(repo, paths.notebooks)
        if repo
        else fold_docs_nbs(list(paths.notebooks.glob("**/*.ipynb")), paths.notebooks)
    )


async def clean(nbs: list[str]):
    """Clean notebooks."""
    async with TaskGroup() as tg:
        for nb in nbs:
            tg.create_task(clean_notebook(nb))


async def execute(nbs: list[str], parameters: dict[str, Any] | None = None):
    """Execute notebooks."""
    with ProcessPoolExecutor() as executor:
        for nb in nbs:
            executor.submit(
                execute_notebook,
                input_path=nb,
                output_path=nb,
                remove_tagged_cells=["ploomber-engine-error-cell"],
                parameters=parameters or {},
            )
    async with TaskGroup() as tg:
        for nb in nbs:
            tg.create_task(clean_notebook(nb))


async def export(nbs: list[str], paths):
    """Export notebooks to Markdown and HTML."""
    async with TaskGroup() as tg:
        for nb in nbs:
            tg.create_task(export_notebook(nb, paths))


async def report(nbs: list[str], paths):
    """Generate DOCX reports."""
    async with TaskGroup() as tg:
        for nb in nbs:
            tg.create_task(
                report_on_notebook(**{
                    kwarg: fold(path)
                    for kwarg, path in dict(
                        workdir=paths.md,
                        template=paths.template,
                        filt=paths.filt,
                        zotero=ZOTERO,
                        csl=paths.csl,
                        docx=paths.docx / Path(nb).with_suffix(".docx").name,
                        md=paths.md / Path(nb).with_suffix(".md").name,
                    ).items()
                })
            )


def commit(repo, paths):
    """Commit changes."""
    docs_dvc_file = fold(paths.notebooks.with_suffix(".dvc"))
    repo.commit(docs_dvc_file, force=True)
    add(repo, docs_dvc_file)


# * -------------------------------------------------------------------------------- * #
# * SINGLE NOTEBOOK PROCESSING


async def clean_notebook(nb: str):
    """Clean a notebook."""
    commands = [
        f"ruff --fix-only {nb}",
        f"ruff format {nb}",
         "nb-clean clean"
         " --remove-empty-cells"
         " --preserve-cell-outputs"
         " --preserve-cell-metadata special tags"
        f" -- {nb}",
    ]  # fmt: skip
    for command in commands:
        await run_process(command)


async def export_notebook(nb: str, paths):
    """Export a notebook to Markdown and HTML."""
    md = fold(paths.md)
    html = fold(paths.html)
    for command in [
        f"jupyter-nbconvert --to markdown --no-input --output-dir {md} {nb}",
        f"jupyter-nbconvert --to html --no-input --output-dir {html} {nb}",
    ]:
        await run_process(command)


def preserve_dir(f: Callable[..., Coroutine[Any, Any, Any]]):
    """Preserve the current directory."""

    @wraps(f)
    async def wrapped(*args, **kwargs):
        return await CoroWrapper(f(*args, **kwargs), PreserveDir())

    return wrapped


@preserve_dir
async def report_on_notebook(
    workdir: str, template: str, filt: str, zotero: str, csl: str, docx: str, md: str
):
    """Generate a DOCX report from a notebook.

    Requires changing the active directory to the Markdown folder outside of this
    asynchronous function, due to how Pandoc generates links inside the documents.
    """
    chdir(workdir)
    await run_process(
        venv=False,
        command=(
            " pandoc"
            # Pandoc configuration
            "   --standalone"  # Don't produce a document fragment.
            "   --from markdown-auto_identifiers"  # Avoids bookmark pollution around Markdown headers
            "   --to docx"  # The output format
            f"  --reference-doc {template}"  # The template to export literature reviews to
            # Custom filter to strip out dataframes
            f"  --filter {filt}"
            # Zotero Lua filter and metadata passed to it
            f"  --lua-filter {zotero}"  # Needs to be the one downloaded from the tutorial page https://retorque.re/zotero-better-bibtex/exporting/pandoc/#from-markdown-to-zotero-live-citations
            "   --metadata zotero_library:3"  # Corresponds to "Nucleate pool boiling [3]"
            f"  --metadata zotero_csl_style:{csl}"  # Must also be installed in Zotero
            # I/O
            f"  --output {docx}"
            f"  {md}"
        ),
    )


# * -------------------------------------------------------------------------------- * #
# * UTILITIES

COLORS = {
    "jupyter-nbconvert": "blue",
    "nb-clean": "magenta",
    "ruff": "cyan",
    "pandoc": "red",
}


async def run_process(command: str, venv: bool = True):
    """Run a subprocess asynchronously."""
    c, *args = split(command)
    file = args[-1].split("/")[-1]
    colored_command = f"<{COLORS[c]}>{c}</{COLORS[c]}>"
    logger.info(f"    <yellow>Start </yellow> {colored_command} {file}")
    message = await notebooks.run_process(command, venv)
    logger.info(
        f"    <green>Finish</green> {colored_command} {file}"
        + ((": " + message.replace("\n", ". ")[:30] + "...") if message else "")
    )


def fold_modified_nbs(repo: Repo, docs: Path) -> list[str]:
    """Fold the paths of modified documentation notebooks."""
    modified = get_modified_files(repo)
    return (
        fold_docs_nbs(modified, docs)
        if any(path.is_relative_to(docs) for path in modified)
        else []
    )


def get_modified_files(repo: Repo) -> list[Path]:
    """Get files considered modified by DVC."""
    status = repo.data_status(granular=True)
    modified: list[Path] = []
    for key in ["modified", "added"]:
        paths = status["uncommitted"].get(key) or []
        paths.extend(status["committed"].get(key) or [])
        modified.extend([Path(path).resolve() for path in paths])
    return modified


def fold_docs_nbs(paths: list[Path], docs: Path) -> list[str]:
    """Fold the paths of documentation-related notebooks."""
    return list({
        fold(nb)
        for nb in sorted({
            path.with_suffix(".ipynb")
            for path in paths
            # Consider notebook modified even if only its `.h5` file is
            if path.is_relative_to(docs) and path.suffix in [".ipynb", ".h5"]
        })
    })


# * -------------------------------------------------------------------------------- * #
# * PRIMITIVES


class PreserveDir:
    """Re-entrant context manager that preserves the current directory.

    Reference: <https://stackoverflow.com/a/64395754/20430423>
    """

    def __init__(self):
        self.outer_dir = Path.cwd()
        self.inner_dir = None

    def __enter__(self):
        self.outer_dir = Path.cwd()
        if self.inner_dir is not None:
            chdir(self.inner_dir)

    def __exit__(self, *exception_info_):
        self.inner_dir = Path.cwd()
        chdir(self.outer_dir)


class CoroWrapper:
    """Wrap `target` to have every send issued in a `context`.

    Reference: <https://stackoverflow.com/a/56079900/1600898>
    """

    def __init__(
        self, target: Coroutine[Any, Any, Any], context: AbstractContextManager[Any]
    ):
        self.target = target
        self.context = context

    # wrap an iterator for use with 'await'
    def __await__(self):
        # unwrap the underlying iterator
        target_iter = self.target.__await__()
        # emulate 'yield from'
        iter_send, iter_throw = target_iter.send, target_iter.throw
        send, message = iter_send, None
        while True:
            # communicate with the target coroutine
            try:
                with self.context:
                    signal = send(message)  # type: ignore  # pyright: 1.1.311
            except StopIteration as err:
                return err.value
            else:
                send = iter_send
            # communicate with the ambient event loop
            try:
                message = yield signal
            except BaseException as err:  # noqa: BLE001
                send, message = iter_throw, err
