from typing import Iterable
from activityassure.activity_profile import SparseActivityProfile


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
