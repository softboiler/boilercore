"""Warnings."""

from collections.abc import Iterable
from typing import NamedTuple
from warnings import filterwarnings

from boilercore.types import Action


class WarningFilter(NamedTuple):
    """A warning filter, e.g. to be unpacked into `warnings.filterwarnings`."""

    action: Action = "ignore"
    message: str = ""
    category: type[Warning] = Warning
    module: str = ""
    lineno: int = 0
    append: bool = False


def filter_boiler_warnings(other_warnings: Iterable[WarningFilter] | None = None):
    """Filter certain warnings for `boiler` projects."""
    for filt in [
        WarningFilter(action="default"),
        *[WarningFilter(action="error", module=r"^boiler.*")],
        *WARNING_FILTERS,
        *(other_warnings or []),
    ]:
        filterwarnings(*filt)


WARNING_FILTERS = [
    # * --------------------------------------------------------------------------------
    # * MARK: DeprecationWarning and PendingDeprecationWarning
    *[
        WarningFilter(category=DeprecationWarning, module=module, message=message)
        for module, message in [
            (r"IPython\.core\.pylabtools", r"backend2gui is deprecated."),
            (r"latexcodec\.codec", r"open_text is deprecated\. Use files\(\) instead"),
            (r"nptyping\.typing_", r"`.+` is a deprecated alias for `.+`\."),
            (r"pybtex\.plugin", r"pkg_resources is deprecated as an API\."),
        ]
    ],
    *[
        WarningFilter(
            category=DeprecationWarning,
            message=rf"Deprecated call to `pkg_resources\.declare_namespace\('{ns}'\)`\.",
        )
        for ns in ["mpl_toolkits", "sphinxcontrib", "zc"]
    ],
    *[
        WarningFilter(
            category=DeprecationWarning, module=r"pytest_harvest.*", message=message
        )
        for message in [
            r"The hookspec pytest_harvest_xdist.+ uses old-style configuration options",
            r"The hookimpl pytest_configure uses old-style configuration options \(marks or attributes\)\.",
        ]
    ],
    # * --------------------------------------------------------------------------------
    # * MARK: EncodingWarning
    WarningFilter(
        category=EncodingWarning, message="'encoding' argument not specified"
    ),
    *[
        WarningFilter(
            category=EncodingWarning,
            module=module,
            message=r"'encoding' argument not specified\.",
        )
        for module in [r"jupyter_client\.connect", r"sphinx.*"]
    ],
    # * --------------------------------------------------------------------------------
    # * MARK: FutureWarning
    WarningFilter(
        category=FutureWarning,
        message=r"A grouping was used that is not in the columns of the DataFrame and so was excluded from the result\. This grouping will be included in a future version of pandas\. Add the grouping as a column of the DataFrame to silence this warning\.",
    ),
    # * --------------------------------------------------------------------------------
    # * MARK: ImportWarning
    WarningFilter(
        # ? Happens during tests under some configurations
        category=ImportWarning,
        message=r"ImportDenier\.find_spec\(\) not found; falling back to find_module\(\)",
    ),
    # * --------------------------------------------------------------------------------
    # * MARK: RuntimeWarning
    *[
        WarningFilter(category=RuntimeWarning, message=message)
        for message in [
            r"Failed to disconnect .* from signal",  # ? https://github.com/pytest-dev/pytest-qt/issues/558#issuecomment-2143975018
            r"invalid value encountered in power",
            r"numpy\.ndarray size changed, may indicate binary incompatibility\. Expected \d+ from C header, got \d+ from PyObject",
            r"Proactor event loop does not implement add_reader family of methods required for zmq.+",
        ]
    ],
    # * --------------------------------------------------------------------------------
    # * MARK: UserWarning
    *[
        WarningFilter(category=UserWarning, message=message)
        for message in [
            r"The palette list has more values \(\d+\) than needed \(\d+\), which may not be intended\.",
            r"To output multiple subplots, the figure containing the passed axes is being cleared\.",
        ]
    ],
    # * --------------------------------------------------------------------------------
    # * MARK: Combinations
    *[
        WarningFilter(
            category=category,
            # module=r"colorspacious\.comparison",  # ? CI still complains
            message=r"invalid escape sequence",
        )
        for category in [DeprecationWarning, SyntaxWarning]
    ],
]
"""Warning filters."""
