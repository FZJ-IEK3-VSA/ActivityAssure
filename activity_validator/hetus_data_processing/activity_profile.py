"""
Defines classes for activity profiles
"""

import copy
from datetime import datetime, time, timedelta
import functools
import logging
import operator
from typing import Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config


# TODO: does not work for some reason
# dataclasses_json.cfg.global_config.encoders[timedelta] = str
# dataclasses_json.global_config.decoders[timedelta] =


@dataclass_json
@dataclass
class Traits:
    """
    A set of characteristics that defines the type of person
    or household, and which category of validation data it
    can be compared to
    """

    traits: dict[str, str] = field(default_factory=dict)
    name: Optional[str] = None

    def add_trait(self, name, value):
        assert name not in self.traits, f"Trait already exists: {name}"
        self.traits[name] = value

    def __getitem__(self, arg):
        """
        Implements [] operator
        """
        return self.traits[arg]


def write_timedelta(d: Optional[timedelta]) -> Optional[str]:
    """
    Converts a timedelta into a str. Necessary to correctly
    represent None as null in json.

    :param d: timedelta to write
    :type d: Optional[timedelta]
    :return: str representation of the timedelta
    :rtype: str
    """
    return str(d) if d else None


def parse_timedelta(s: str) -> timedelta:
    """
    Parses a timedelta object from a string. Only supports a
    resolution up to seconds.

    :param s: the string to parse the timedelta from
    :type s: str
    :return: parsed timedelta object
    :rtype: timedelta
    """
    days = 0
    if "day" in s:
        # s has the format 'X days, XX:XX:XX'
        i1 = s.find("day")
        days = int(s[:i1].strip())
        assert "," in s, f"Unexpected timedelta format: {s}"
        i2 = s.find(",")
        time_str = s[i2 + 1 :].strip()
    else:
        # s has the format 'XX:XX:XX'
        time_str = s
    t = datetime.strptime(time_str, "%H:%M:%S")
    return timedelta(days=days, hours=t.hour, minutes=t.minute, seconds=t.second)


@dataclass_json
@dataclass
class ActivityProfileEntryTime:
    """
    Simple class for storing an activity, i.e. a single entry in
    an activity profile. For HETUS data this corresponds to a
    consecutive block of diary time slots with the same code.
    """

    #: activity name or code
    name: str
    #: activity start
    start: datetime = field(
        metadata=config(encoder=lambda d: d.isoformat(), decoder=datetime.fromisoformat)
    )
    #: duration of activity
    duration: timedelta | None = field(
        default=None,
        metadata=config(encoder=write_timedelta, decoder=parse_timedelta),
    )

    def end(self) -> datetime | None:
        """
        Returns the end date of the activity

        :return: end date of the activity
        :rtype: datetime
        """
        return self.start + self.duration if self.duration else None

    def split(self, split_time: time) -> list["ActivityProfileEntryTime"]:
        """
        Divides this ActivityProfileEntry into multiple entries, splitting at the
        specified time on each day (for multi-day activities).

        :return: the list of activity profile entries
        :rtype: list[ActivityProfileEntryTime]
        """
        if self.duration is None:
            # duration is unknown, so splitting is not possible
            return [self]
        split_date = datetime.combine(self.start.date(), split_time, self.start.tzinfo)
        if split_date < self.start:
            # no split on first calendar day of activity
            split_date += timedelta(days=1)
        end_date = self.start + self.duration
        current_start = self.start
        day_profiles = []
        while split_date < end_date:
            # for each day, add a new activity entry
            day_profiles.append(
                ActivityProfileEntryTime(
                    self.name, current_start, split_date - current_start
                )
            )
            current_start = split_date
            split_date += timedelta(days=1)
        day_profiles.append(
            ActivityProfileEntryTime(self.name, current_start, end_date - current_start)
        )
        return day_profiles


@dataclass_json
@dataclass
class ActivityProfileEntry:
    """
    Simple class for storing an activity, i.e. a single entry in
    an activity profile. For HETUS data this corresponds to a
    consecutive block of diary time slots with the same code.
    """

    #: activity name or code
    name: str
    #: 0-based index of activity start
    start: int
    #: duration of activity in time steps
    duration: Optional[int] = None


@dataclass_json
@dataclass
class ActivityProfile:
    """
    Class for storing a single activity profile, of a single person
    on a single day.
    """

    #: list of activity objects
    activities: list[ActivityProfileEntryTime | ActivityProfileEntry]
    #: characteristics of the person this profile belongs to
    traits: Traits = field(default_factory=Traits)

    def calc_durations(self, profile_end=None) -> None:
        """
        Calculates and sets the duration for each contained activity.

        :param profile_end: the end of the whole profile, necessary
                            for calculating the duration of the last
                            activity
        """
        assert self.activities, "Empty activity list"
        for i, a in enumerate(self.activities[:-1]):
            assert a.duration is None, f"Duration was already set: {a.duration}"
            a.duration = self.activities[i + 1].start - a.start
        if profile_end is not None:
            # if the overall end is specified, the duration of the last
            # activity can be calculated
            last_activity = self.activities[-1]
            last_activity.duration = profile_end - last_activity.start

    def total_duration(self) -> float | timedelta | None:
        # calculate the sum of activity durations without having to
        # specify a starting value
        return functools.reduce(operator.add, (a.duration for a in self.activities))

    def split_day_profiles(
        self,
        day_change_time: time,
    ) -> list["ActivityProfile"]:
        """
        Splits this activity profile into a separate profile for each day.

        :param day_change_time: the date switch time to use for splitting,
                                defaults to DAY_CHANGE_TIME
        :type day_change_time: time, optional
        :return: a list of single-day activity profiles
        :rtype: list[ActivityProfile]
        """
        # split all activities that cross day switch time and put them in one list
        all_split_activities = [
            sa for a in self.activities for sa in a.split(day_change_time)
        ]
        start = all_split_activities[0].start
        # determine datetime of first day switch
        next_split = datetime.combine(start.date(), day_change_time, start.tzinfo)
        if next_split < start:
            # no split on first calendar day of activity
            next_split += timedelta(days=1)
        day_profiles = []
        current_day_profile = []
        for i, activity in enumerate(all_split_activities):
            if activity.duration is None:
                assert (
                    i == len(all_split_activities) - 1
                ), "No duration for other than the last activity"
                # last activity of the whole profile
                logging.info(
                    "Skipped last day during splitting due to missing duration of last activity"
                )
                break

            if activity.end() < next_split:
                # activity still ends on the previous day
                current_day_profile.append(activity)
                continue
            assert (
                activity.end() == next_split
            ), "An activity was not correctly split at day switch"
            # day switch
            current_day_profile.append(activity)
            day_profiles.append(
                ActivityProfile(current_day_profile, copy.deepcopy(self.traits))
            )
            current_day_profile = []
            next_split += timedelta(days=1)
        return day_profiles


@dataclass_json
@dataclass
class HHActivityProfiles:
    """
    Bundles the activity profiles from all people in one household
    """

    activity_profiles: dict[str, ActivityProfile] = field(default_factory=dict)

    household: Optional[str] = None
