from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
from activityassure.activity_profile import SparseActivityProfile


@dataclass
class ActivityStatistics:
    activity: str
    shares: list[float]
    durations: list[timedelta]
    durations_without: list[timedelta]

    def save(self, path: Path) -> None:
        """
        Save the statistics to a file
        :param path: path to the file
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        shares_series = pd.Series(self.shares, name="shares")
        durations_series = pd.Series(self.durations, name="durations")
        durations_without_series = pd.Series(
            self.durations_without, name="durations_without"
        )
        data = pd.concat(
            [shares_series, durations_series, durations_without_series], axis=1
        )
        data.to_csv(path)

    @staticmethod
    def load(path: Path) -> "ActivityStatistics":
        """
        Load the statistics from a file
        :param path: path to the file
        :return: ActivityStatistics object
        """
        data = pd.read_csv(path)
        shares = data["shares"].tolist()
        durations = pd.to_timedelta(data["durations"]).tolist()
        durations_without = pd.to_timedelta(data["durations_without"]).tolist()
        return ActivityStatistics(
            activity=path.stem,
            shares=shares,
            durations=durations,
            durations_without=durations_without,
        )


class StatisticsCalculator:
    """
    Calculates statistics for one type of activity in an activity profile
    """

    def __init__(
        self,
        profile: SparseActivityProfile,
        activity_name: str,
        ignore: Iterable[str] = [],
    ):
        self.profile = profile
        self.activity = activity_name

        self.ignore = set(ignore)

        # collect the relevant activities
        self.activities = [a for a in profile.activities if a.name == self.activity]

    def overall_share(self) -> float:
        """
        Calculate the overall share of an activity in a profile
        :return: share of the activity in the profile
        """
        act_duration = sum(a.duration for a in self.activities)
        return act_duration / self.profile.length()

    def durations(self):
        durations = [a.duration * self.profile.resolution for a in self.activities]
        return durations

    def durations_without_act(self):
        durations = [
            (self.activities[i + 1].start - a.end()) * self.profile.resolution
            for i, a in enumerate(self.activities[:-1])
        ]
        return durations
