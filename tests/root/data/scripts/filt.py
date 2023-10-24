"""Filter tables from Pandoc input."""

from dataclasses import dataclass
from typing import Any

from pandocfilters import toJSONFilter

REMOVE: list[Any] = []
"""Signals the removal of a block."""

memory: list[str] = []
"""Memory of block keys for multi-block matching."""


def main(
    key: str, _value: str, _format: str, _meta: dict[str, Any]
) -> list[Any] | None:
    checks = [check_table(key)]
    if memory and not any(c.match for c in checks):
        memory.clear()
    if any(c.remove for c in checks):
        return REMOVE  # Remove this block


@dataclass
class Check:
    """Whether the current block is part of a match, and whether to remove it."""

    match: bool = True
    """Whether the current block is part of a match."""

    remove: bool = True
    """Whether to remove the current block."""


TABLE = ["RawBlock", "Plain", "Str"]
"""Sequence of blocks representing a table."""


def check_table(key: str) -> Check:
    if key == TABLE[0]:
        memory.append(key)
        return Check()
    if memory and key == TABLE[1] and memory[-1] == TABLE[0]:
        memory.append(key)
        return Check()
    if memory and key == TABLE[2] and memory[-2:] == TABLE[:2]:
        return Check()
    return Check(match=False, remove=False)


if __name__ == "__main__":
    toJSONFilter(main)
