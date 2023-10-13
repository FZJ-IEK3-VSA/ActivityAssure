"""
Defines classes for activity profiles
"""

from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
import pandas as pd
from activity_validator.hetus_data_processing import hetus_constants

from activity_validator.hetus_data_processing.attributes import (
    diary_attributes,
    person_attributes,
)


DEFAULT_RESOLUTION = timedelta(minutes=1)


@dataclass_json
@dataclass(unsafe_hash=True)  # TODO: better make it frozen?
class ProfileType:
    """
    A set of characteristics that defines the type of a
    sinlge-day activity profile and identifies matching
    validation data.
    """

    country: str | None = None
    sex: person_attributes.Sex | None = None
    work_status: person_attributes.WorkStatus | None = None
    day_type: diary_attributes.DayType | None = None

    def to_tuple(self) -> tuple[str, str, str, str]:
        return (
            str(self.country),
            str(self.sex),
            str(self.work_status),
            str(self.day_type),
        )

    @staticmethod
    def from_strs(values: Iterable[str]) -> "ProfileType":
        """
        Creates a ProfileType object from an iterable containing
        the characteristics as strings.

        :param values: the characteristics as strs
        :type values: Iterable[str]
        :return: the corresponding ProfileType object
        :rtype: ProfileType
        """
        country, sex, work_status, day_type = values
        try:
            profile_type = ProfileType(
                country,
                person_attributes.Sex(sex),
                person_attributes.WorkStatus(work_status),
                diary_attributes.DayType(day_type),
            )
        except KeyError as e:
            assert False, f"Invalid key: {e}"
        return profile_type


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
    duration: int = -1

    def end(self) -> int:
        """
        Returns the end timestep of the activity

        :return: end timestep of the activity
        """
        assert self.duration > 0, f"Invalid duration: {self.duration}"
        return self.start + self.duration

    def split(
        self, first_split: int, timesteps_per_day: int
    ) -> list["ActivityProfileEntry"]:
        """
        Divides this ActivityProfileEntry into multiple entries, splitting at the specified
        timestep and, for activities >24 h, at the same timestep 24 h later.

        :return: the list of activity entries
        """
        assert (
            self.start <= first_split <= self.end()
        ), "Split timestep is outside of activity time frame"

        # the section until the first split
        first_section = ActivityProfileEntry(
            self.name, self.start, first_split - self.start
        )
        # the remaining sections
        entries = [first_section] + [
            ActivityProfileEntry(self.name, start, timesteps_per_day)
            for start in range(first_split, self.end(), timesteps_per_day)
        ]
        # fix duration of last section
        entries[-1].duration = self.end() - entries[-1].start
        return entries


def get_person_traits(
    person_traits: dict[str, ProfileType], filepath: str
) -> ProfileType:
    """
    Extracts the person name from the path of an activity profile file
    and returns the matching ProfileType object with the person
    characteristics.

    :param person_traits: the person trait dict
    :param filepath: path of the activity profile file, contains the
                     name of the person
    :raises RuntimeError: when no characteristics for the person were
                          found
    :return: the characteristics of the person
    """
    name = Path(filepath).stem
    if name not in person_traits:
        raise RuntimeError(f"No person characteristics found for '{name}'")
    return person_traits[name]


@dataclass_json
@dataclass
class ActivityProfile:
    # TODO rename to SparseProfile
    """
    Class for storing a single activity profile, of a single person
    on a single day.
    """

    #: list of activity objects
    activities: list[ActivityProfileEntry]
    #: time offset from midnight
    offset: timedelta = field(
        metadata=config(encoder=write_timedelta, decoder=parse_timedelta),
    )
    #: duration of one timestep
    resolution: timedelta = field(
        metadata=config(encoder=write_timedelta, decoder=parse_timedelta),
    )
    #: characteristics of the person this profile belongs to
    profile_type: ProfileType = field(default_factory=ProfileType)

    @staticmethod
    def load_from_csv(
        path,
        person_traits: dict[str, ProfileType],
        resolution: timedelta = DEFAULT_RESOLUTION,
    ) -> "ActivityProfile":
        """
        Loads an ActivityProfile from a csv file.

        :param path: path to the csv file
        :param timestep: timestep resolution of the profile, defaults to DEFAULT_RESOLUTION
        :return: the loaded ActivityProfile
        """
        assert timedelta(days=1) % resolution == timedelta(
            0
        ), "Resolution has to be a divisor of 1 day"
        data = pd.read_csv(path)
        # pd.to_datetime(data["Date"])
        entries = [
            ActivityProfileEntry(row["Activity"], row["Timestep"])
            for _, row in data.iterrows()
        ]
        # calculate offset (timedelta since last midnight)
        first_date = datetime.fromisoformat(data["Date"][0])
        offset = first_date - datetime.combine(first_date.date(), time())
        assert offset % resolution == timedelta(
            0
        ), "Start time has to be a divisor of the resolution"
        profile_type = get_person_traits(person_traits, path)
        profile = ActivityProfile(entries, offset, resolution, profile_type)
        profile.remove_timestep_offset()
        profile.calc_durations()
        # remove the last activity (duration is unknown)
        profile.activities.pop()
        return profile

    def remove_timestep_offset(self) -> None:
        """
        Removes any timestep offset, so that the first activity
        starts at timestep 0.
        """
        offset = self.activities[0].start
        if offset == 0:
            return
        for activity in self.activities:
            activity.start -= offset

    def calc_durations(self, profile_end: int | None = None) -> None:
        """
        Calculates and sets the duration for each contained activity.

        :param profile_end: the end of the whole profile, necessary
                            for calculating the duration of the last
                            activity
        """
        assert self.activities, "Empty activity list"
        for i, a in enumerate(self.activities[:-1]):
            assert a.duration == -1, f"Duration was already set: {a.duration}"
            a.duration = self.activities[i + 1].start - a.start
        if profile_end is not None:
            # if the overall end is specified, the duration of the last
            # activity can be calculated
            last_activity = self.activities[-1]
            last_activity.duration = profile_end - last_activity.start

    def start(self) -> int:
        return self.activities[0].start

    def end(self) -> int:
        return self.activities[-1].end()

    def length(self) -> int:
        return self.end() - self.start()

    def duration(self) -> timedelta:
        return self.length() * self.resolution

    def split_into_day_profiles(
        self,
        split_offset: timedelta = hetus_constants.PROFILE_OFFSET,
    ) -> list["ActivityProfile"]:
        """
        Splits this activity profile into multiple single-day profiles using the
        specified split_offset as splitting time for each day.

        :param split_offset: the offset from midnight to the date switch time
        :return: a list of single-day activity profiles
        """
        assert timedelta(1) % self.resolution == timedelta(
            0
        ), f"Invalid resolution: {self.resolution}"
        timesteps_per_day = int(timedelta(days=1) / self.resolution)
        # calculate timestep of first split
        next_split = int((split_offset - self.offset) / self.resolution)
        assert split_offset % self.resolution == timedelta(
            0
        ), f"Invalid split offset: {split_offset}"
        if next_split <= 0:
            # first split is on the next day
            next_split += timesteps_per_day

        day_profiles: list[ActivityProfile] = []
        current_day_profile: list[ActivityProfileEntry] = []
        for activity in self.activities:
            if activity.end() >= next_split:
                # the activity lasts over the specified day switch time
                split_sections = activity.split(next_split, timesteps_per_day)
                assert len(split_sections) > 0, "Invalid split"
                # add the profile for the past day
                current_day_profile.append(split_sections[0])
                day_profiles.append(
                    ActivityProfile(
                        current_day_profile,
                        split_offset,
                        self.resolution,
                        self.profile_type,
                    )
                )
                # add intermediate 24 h split sections as separate profile
                day_profiles.extend(
                    ActivityProfile(
                        [a],
                        split_offset,
                        self.resolution,
                        self.profile_type,
                    )
                    for a in split_sections[1:-1]
                )
                # add the last section to the list for the following day
                current_day_profile = [split_sections[-1]]
                # increment the timestep for the next split
                next_split += timesteps_per_day * (len(split_sections) - 1)
            else:
                # the activity does not need to be split
                current_day_profile.append(activity)
        # TODO if necessary, call remove_timestep_offset on each new profile
        return day_profiles


@dataclass_json
@dataclass
class HHActivityProfiles:
    """
    Bundles the activity profiles from all people in one household
    """

    activity_profiles: dict[str, ActivityProfile] = field(default_factory=dict)

    household: Optional[str] = None
