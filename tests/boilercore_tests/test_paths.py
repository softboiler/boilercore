"""Tests for the paths module."""

from datetime import datetime

import pytest

from boilercore.paths import ISOLIKE, dt_fromisolike

MILLENNIA = "20"
DECADE = MONTH = DAY = HOUR = MINUTE = SECOND = "01"
SHORTDATE = f"{DECADE}-{MONTH}-{DAY}"
DATE = f"{MILLENNIA}{SHORTDATE}"
TIME = f"{HOUR}:{MINUTE}:{SECOND}"
DATETIME = f"{DATE}T{TIME}"


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        *(
            pytest.param(string, datetime.fromisoformat(string), id=string)
            for string in (
                f"{DATE}T{HOUR}Z",
                f"{DATE}T{HOUR}+{HOUR}:{MINUTE}",
                f"{DATE}T{TIME}-{HOUR}:{MINUTE}",
            )
        ),
        *(
            pytest.param(string, datetime.fromisoformat(DATETIME), id=string)
            for string in (
                DATETIME,
                f"{SHORTDATE}T{TIME}",
                DATETIME.replace("T", "t"),
                DATETIME.replace(":", "-"),
                DATETIME.replace(":", "$").replace("-", "$"),
            )
        ),
        *(
            pytest.param(string, datetime.fromisoformat(fullstring), id=string)
            for string, fullstring in {f"{DATE}T{HOUR}": f"{DATE}T{HOUR}:00:00"}.items()
        ),
    ],
)
def test_isolike(string, expected):
    """Test the isolike function."""
    if match := ISOLIKE.fullmatch(string):
        assert dt_fromisolike(match) == expected
    else:
        raise ValueError(f"Could not parse {string} as isolike.")
