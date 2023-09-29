"""Common functionality of boiler repositories."""

from collections.abc import Sequence
from itertools import chain
from pathlib import Path
from typing import Literal, NamedTuple, TypeAlias
from warnings import filterwarnings

PROJECT_PATH = Path()


def get_params_file():
    return PROJECT_PATH / "params.yaml"


Action: TypeAlias = Literal["default", "error", "ignore", "always", "module", "once"]


class WarningFilter(NamedTuple):
    """A warning filter, e.g. to be unpacked into `warnings.filterwarnings`."""

    action: Action = "ignore"
    message: str = ""
    category: type[Warning] = Warning
    module: str = ""
    lineno: int = 0
    append: bool = False


NO_WARNINGS = []


def filter_certain_warnings(
    warnings: Sequence[WarningFilter] = NO_WARNINGS, root_action: Action = "error"
):
    """Filter certain warnings for a package."""
    filterwarnings(root_action)
    for filt in [
        *chain.from_iterable(
            get_warnings_as_errors_for_src(category)
            for category in [
                DeprecationWarning,
                PendingDeprecationWarning,
                EncodingWarning,
            ]
        ),
        *warnings,
    ]:
        filterwarnings(*filt)


def get_warnings_as_errors_for_src(
    category: type[Warning],
    action: Action = "error",
    third_party_action: Action = "default",
) -> tuple[WarningFilter, WarningFilter]:
    """Get filter which sets warnings as errors only for the package in `src`."""
    package = next(path for path in Path("src").iterdir() if path.is_dir()).name
    all_package_modules = rf"{package}\..*"
    return (
        WarningFilter(action=third_party_action, category=category),
        WarningFilter(action=action, category=category, module=all_package_modules),
    )
