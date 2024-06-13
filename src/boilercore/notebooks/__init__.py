"""Formatting and display utilities."""

from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from shlex import split
from subprocess import CalledProcessError
from typing import Any

import pandas as pd
from IPython.core.display import Markdown, Math
from IPython.display import display
from sympy import FiniteSet
from sympy.printing.latex import latex


def set_format():
    """Set up formatting for interactive notebook sessions.

    The triple curly braces in the f-string allows the format function to be dynamically
    specified by a given float specification. The intent is clearer this way, and may be
    extended in the future by making `float_spec` a parameter.
    """
    float_spec = ":#.4g"
    pd.options.display.min_rows = pd.options.display.max_rows = 50
    pd.options.display.float_format = f"{{{float_spec}}}".format


def disp_named(*args: tuple[Any, str]):
    """Display objects with names above them."""
    for elem, name in args:
        display(Markdown(f"##### {name}"))
        display(elem)


def disp_free(title, eqn, **kwargs):
    """Display free symbols."""
    disp(title, eqn, **kwargs)
    disp("Free symbols", FiniteSet(*eqn.rhs.free_symbols), **kwargs)


def disp(title, *exprs, **kwargs):
    """Display equation."""
    print(f"{title}:")  # noqa: T201
    display(*(math_mod(expr, **kwargs) for expr in exprs))


def math_mod(expr, long_frac_ratio=3, **kwargs):
    """Represent expression as LaTeX math."""
    return Math(latex(expr, long_frac_ratio=long_frac_ratio, **kwargs))


async def clean(nb: str):
    """Clean a notebook."""
    commands = [
        f"ruff --fix-only {nb}",
        f"ruff format {nb}",
         "   nb-clean clean --remove-empty-cells"
         "     --preserve-cell-outputs"
         "     --preserve-cell-metadata special tags"
        f"    -- {nb}",
    ]  # fmt: skip
    for command in commands:
        await run_process(command)


async def run_process(command: str, venv: bool = True) -> str:
    """Run a process asynchronously."""
    command, *args = split(command)
    process = await create_subprocess_exec(
        f"{'.venv/scripts/' if venv else ''}{command}", *args, stdout=PIPE, stderr=PIPE
    )
    stdout, stderr = (msg.decode("utf-8") for msg in await process.communicate())  # type: ignore  # pyright 1.1.347  # Implicit iter
    message = (
        (f"{stdout}\n{stderr}" if stdout and stderr else stdout or stderr)
        .replace("\r\n", "\n")
        .strip()
    )
    if process.returncode:
        exception = CalledProcessError(
            returncode=process.returncode, cmd=command, output=stdout, stderr=stderr
        )
        exception.add_note(message)
        exception.add_note("Arguments:\n" + "    \n".join(args))
        raise exception
    return message
