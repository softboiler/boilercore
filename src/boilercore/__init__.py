"""Common functionality of boiler repositories."""

from collections.abc import Sequence
from importlib.machinery import ModuleSpec
from itertools import chain
from pathlib import Path
from types import ModuleType
from typing import NamedTuple
from warnings import filterwarnings

from boilercore.paths import get_module_name
from boilercore.types import Action

PROJECT_PATH = Path()


def get_params_file():  # noqa: D103
    return PROJECT_PATH / "params.yaml"


class WarningFilter(NamedTuple):
    """A warning filter, e.g. to be unpacked into `warnings.filterwarnings`."""

    action: Action = "ignore"
    message: str = ""
    category: type[Warning] = Warning
    module: str = ""
    lineno: int = 0
    append: bool = False


DEFAULT_CATEGORIES = [DeprecationWarning, PendingDeprecationWarning, EncodingWarning]
ERROR = "error"
DEFAULT = "default"
NO_WARNINGS = []


def filter_certain_warnings(
    package: ModuleType | ModuleSpec | Path | str,
    categories: Sequence[type[Warning]] = DEFAULT_CATEGORIES,
    root_action: Action | None = ERROR,
    package_action: Action = ERROR,
    other_action: Action = DEFAULT,
    other_warnings: Sequence[WarningFilter] = NO_WARNINGS,
):
    """Filter certain warnings for a package."""
    for filt in [
        # Optionally filter warnings with the root action
        *([WarningFilter(action=root_action)] if root_action else []),
        # Filter certain categories with a package action, and third-party action otherwise
        *chain.from_iterable(
            filter_package_warnings(
                package=package,
                category=category,
                action=package_action,
                other_action=other_action,
            )
            for category in categories
        ),
        # Ignore this as it crops up only during test time under some configurations
        WarningFilter(
            message=r"ImportDenier\.find_spec\(\) not found; falling back to find_module\(\)",
            category=ImportWarning,
        ),
        # Additionally filter these other warnings
        *other_warnings,
    ]:
        filterwarnings(*filt)


def filter_package_warnings(
    package: ModuleType | ModuleSpec | Path | str,
    category: type[Warning],
    action: Action = ERROR,
    other_action: Action = DEFAULT,
) -> tuple[WarningFilter, WarningFilter]:
    """Get filter which filters warnings differently for the package."""
    all_package_modules = rf"{get_module_name(package)}\..*"
    return (
        WarningFilter(action=other_action, category=category),
        WarningFilter(action=action, category=category, module=all_package_modules),
    )
