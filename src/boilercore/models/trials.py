"""Trials."""

import datetime
import re
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic.v1 import BaseModel, DirectoryPath, Field, FilePath, validator

from boilercore.models import YamlModel
from boilercore.models.geometry import Geometry
from boilercore.types import Coupon, Group, Joint, Rod, Sample


class Trial(BaseModel):
    """A trial."""

    # ! META FIELDS ADDED TO DATAFRAME

    # !! DATE

    date: datetime.date = Field(
        default=..., description="The date of the trial.", exclude=True
    )

    @validator("date", pre=True)
    @classmethod
    def validate_date(cls, date):
        """Validate a date."""
        return datetime.date.fromisoformat(date)

    group: Group
    rod: Rod
    coupon: Coupon
    sample: Sample | None
    joint: Joint
    good: bool = Field(default=True, description="Whether the boiling curve is good.")
    plot: bool = Field(
        default=False, description="Whether this trial should be plotted."
    )

    # ! FIELDS TO EXCLUDE FROM DATAFRAME

    @property
    def timestamp(self):
        """Trial timestamp."""
        return pd.Timestamp(self.date)

    # Loaded from config, but not propagated to dataframes. Not readable in a table
    # anyways, and NA-handling results in additional ~40s to pipeline due to the need to
    # use slow "fillna".
    comment: str = Field(default="", exclude=True)

    # ! PROJECT-DEPENDENT SETUP

    # Can't be None. Set in Project.__init__()
    path: DirectoryPath = Field(default=None, exclude=True)
    run_files: list[FilePath] = Field(default=None, exclude=True)
    run_index: list[tuple[pd.Timestamp, pd.Timestamp]] = Field(
        default=None, exclude=True
    )
    thermocouple_pos: dict[str, float] = Field(default=None, exclude=True)

    def setup(self, paths, geometry: Geometry, copper_temps: list[str]):
        """Set up the trial."""
        self.set_paths(paths)
        self.set_geometry(geometry, copper_temps)

    def set_paths(self, paths):
        """Get the path to the data for this trial. Called during project setup."""
        trial_base = paths.trials / self.date.isoformat()
        self.path = trial_base
        self.run_files = sorted(self.path.glob("*.csv"))
        if not self.run_files:
            raise FileNotFoundError(f"No runs found in {self.path}.")
        self.set_index()

    def set_index(self):
        """Get the multiindex for all runs. Called during project setup."""
        run_re = re.compile(r"(?P<date>.*)T(?P<time>.*)")
        run_index: list[tuple[pd.Timestamp, pd.Timestamp]] = []
        for run_file in self.run_files:
            run_time = run_file.stem.removeprefix("results_")

            if m := run_re.match(run_time):
                run_time = f"{m['date']}T{m['time'].replace('-', ':')}"
            else:
                raise AttributeError(f"Could not parse run time: {run_time}")

            trial_date = self.date.isoformat()  # for input to fromisoformat() below
            run_index.append(
                tuple(  # type: ignore  # It's indeterminate but we hard-code the inputs  # pyright 1.1.325
                    pd.Timestamp.fromisoformat(item) for item in (trial_date, run_time)
                )
            )
        self.run_index = run_index

    def set_geometry(self, geometry: Geometry, copper_temps: list[str]):
        """Get relevant geometry for the trial."""
        thermocouple_pos = list(
            np.array(geometry.rods[self.rod]) + np.array(geometry.coupons[self.coupon])
        )
        self.thermocouple_pos = dict(zip(copper_temps, thermocouple_pos, strict=True))


class Trials(YamlModel):
    """The trials."""

    trials: list[Trial]

    def __init__(self, data_file: Path):
        super().__init__(data_file)
