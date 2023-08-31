"""Common functionality of boiler repositories."""

from collections.abc import Sequence
from contextlib import contextmanager
from typing import Literal, NamedTuple
from warnings import catch_warnings, filterwarnings


class WarningFilter(NamedTuple):
    """A warning filter, e.g. to be unpacked into `warnings.filterwarnings`."""

    action: Literal["default", "error", "ignore", "always", "module", "once"] = "ignore"
    message: str = ""
    category: type[Warning] = Warning
    module: str = ""
    lineno: int = 0
    append: bool = False


ENCODING_WARNINGS = [
    *(
        WarningFilter(
            message=r"'encoding' argument not specified",
            category=(category := EncodingWarning),
            module=module,
        )
        for module in (
            "cv2.load_config_py3",
            "dask.config",
            "dill._dill",
            "dvc_objects.fs.local",
            "fsspec.spec",
            "matplotlib.font_manager",
            "ploomber_core.config",
            "pyvisa.util",
            "ruamel.yaml.main",
            "sqltrie.sqlite.sqlite",
            "zc.lockfile",
        )
    ),
    *(
        WarningFilter(
            message=r"UTF-8 Mode affects locale\.getpreferredencoding\(\)\. Consider locale\.getencoding\(\) instead\.",
            category=category,
            module=module,
        )
        for module in ("dill.logger", "scmrepo.git.backend.pygit2")
    ),
]
"""Encoding warnings."""

ALL_WARNINGS = ENCODING_WARNINGS
"""Warning filters common to boiler repositories."""


@contextmanager
def catch_certain_warnings(warnings: Sequence[WarningFilter] = ALL_WARNINGS):
    """Catch certain warnings."""
    with catch_warnings() as context:
        filter_certain_warnings(warnings)
        yield context


def filter_certain_warnings(warnings: Sequence[WarningFilter] = ALL_WARNINGS):
    """Filter certain warnings."""
    for filt in warnings:
        filterwarnings(*filt)
