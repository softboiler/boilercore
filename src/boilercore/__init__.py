"""Common functionality of boiler repositories."""

from collections.abc import Sequence
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from typing import Literal, NamedTuple
from warnings import catch_warnings, filterwarnings

PROJECT_PATH = Path()


def get_params_file():
    return PROJECT_PATH / "params.yaml"


class WarningFilter(NamedTuple):
    """A warning filter, e.g. to be unpacked into `warnings.filterwarnings`."""

    action: Literal["default", "error", "ignore", "always", "module", "once"] = "ignore"
    message: str = ""
    category: type[Warning] = Warning
    module: str = ""
    lineno: int = 0
    append: bool = False


NO_WARNINGS = []


@contextmanager
def catch_certain_warnings(
    package: str, warnings: Sequence[WarningFilter] = NO_WARNINGS
):
    """Catch certain warnings for a package."""
    with catch_warnings() as context:
        filter_certain_warnings(package, warnings)
        yield context


def filter_certain_warnings(
    package: str, warnings: Sequence[WarningFilter] = NO_WARNINGS
):
    """Filter certain warnings for a package."""
    filterwarnings("error")
    for filt in [*get_other_encoding_warnings(package), *warnings]:
        filterwarnings(*filt)


def get_other_encoding_warnings(package: str) -> list[WarningFilter]:
    """Get list of encoding warning filters, keeping those from the package enabled."""
    return list(
        chain.from_iterable(
            get_other_encoding_warning(
                package=package,
                message=message,
                category=EncodingWarning,
            )
            for message in [
                r"'encoding' argument not specified",
                r"UTF-8 Mode affects locale\.getpreferredencoding\(\)\. Consider locale\.getencoding\(\) instead\.",
            ]
        )
    )


def get_other_encoding_warning(
    package: str, message: str, category: type[Warning]
) -> list[WarningFilter]:
    """Get a filter which will only enable warnings emitted by the package."""
    all_package_modules = rf"{package}\..*"
    return [
        WarningFilter(action="ignore", message=message, category=category),
        WarningFilter(
            action="error",
            message=message,
            category=category,
            module=all_package_modules,
        ),
    ]
