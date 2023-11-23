"""
Defines classes for activity profiles
"""

from datetime import datetime, time, timedelta
import itertools
import logging
from pathlib import Path
from typing import Collection, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
import numpy as np
import pandas as pd
from activity_validator.hetus_data_processing import hetus_constants, utils

from activity_validator.hetus_data_processing.attributes import (
    diary_attributes,
    person_attributes,
)

#: default resolution for input data # TODO: remove?
DEFAULT_RESOLUTION = timedelta(minutes=1)

#: path for result data # TODO: move to config file
VALIDATION_DATA_PATH = Path() / "data" / "validation_data"


@dataclass_json
@dataclass(frozen=True)
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
        """
        Returns a tuple representation of this profile type.

        :return: a tuple containing the characteristics of this
                 profile type
        """
        return (
            str(self.country),
            str(self.sex),
            str(self.work_status),
            str(self.day_type),
        )

    def __str__(self) -> str:
        """
        Returns a string representation of this profile type

        :return: a str containing the characteristics of this
                 profile type
        """
        return "_".join(str(c) for c in self.to_tuple())

    def construct_filename(self, name: str = "") -> str:
        return f"{name}_{self}"

    @staticmethod
    def from_filename(filepath: Path) -> tuple[str, Optional["ProfileType"]]:
        components = filepath.stem.split("_")
        basename = components[0]
        if len(components) > 1:
            profile_type = ProfileType.from_iterable(components[1:])
        else:
            profile_type = None
        return basename, profile_type

    @staticmethod
    def from_iterable(values: Collection[str]) -> "ProfileType":
        """
        Creates a ProfileType object from an iterable containing
        the characteristics as strings.

        :param values: the characteristics as strs
        :return: the corresponding ProfileType object
        """
        assert len(values) == 4, f"Invalid number of characteristics: {values}"
        # extract characteristics
        country, sex, work_status, day_type = values
        try:
            profile_type = ProfileType(
                country,
                person_attributes.Sex(sex),
                person_attributes.WorkStatus(work_status),
                diary_attributes.DayType(day_type),
            )
        except KeyError as e:
            assert False, f"Invalid enum key: {e}"
        return profile_type


def create_result_path(
    subdir: str,
    name: str,
    profile_type: ProfileType | None = None,
    base_path: Path | None = None,
    ext: str = "csv",
) -> Path:
    """
    Creates a full result path for saving a file within
    the main result data directory.

    :param subdir: subdirectory to save the file at
    :param name: base name of the file
    :param profile_type: the category of the profile data,
                         if applicable; is appended to the
                         filename; defaults to None
    :param base_path: base directory for the file,
                      defaults to VALIDATION_DATA_PATH
    :param ext: file extension, defaults to "csv"
    """
    if not base_path:
        base_path = VALIDATION_DATA_PATH
    if profile_type is not None:
        # add profile type to filename
        name = profile_type.construct_filename(name)
    name += f".{ext}"
    directory = base_path / subdir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    return path


def convert_to_timedelta(data: pd.DataFrame) -> None:
    for col in data.columns:
        data[col] = pd.to_timedelta(data[col])


def save_df(
    data: pd.DataFrame,
    subdir: str,
    name: str,
    profile_type: ProfileType | None = None,
    base_path: Path = VALIDATION_DATA_PATH,
    ext: str = "csv",
) -> None:
    """
    Saves a result data frame to a csv file within the
    main data directory.

    :param data: data to save
    :param subdir: subdirectory to save the file at
    :param name: base name of the file
    :param profile_type: the category of the profile data,
                         if applicable; is appended to the
                         filename; defaults to None
    :param base_path: base directory for the file,
                      defaults to VALIDATION_DATA_PATH
    :param ext: file extension, defaults to "csv"
    """
    path = create_result_path(subdir, name, profile_type, base_path, ext)
    data.to_csv(path)
    logging.debug(f"Created DataFrame file {path}")


def load_df(
    path: str | Path, as_timedelta: bool = False
) -> tuple[ProfileType | None, pd.DataFrame]:
    """
    Loads a data frame from a csv file.

    :param path: path to the csv file
    :param as_timedelta: whether the DataFrame contains timedelta
                         values, defaults to False
    :return: the ProfileType determined from the filename and the
             loaded DataFrame
    """
    if isinstance(path, str):
        path = Path(path)
    # determine the profile type from the filename
    name, profile_type = ProfileType.from_filename(path)
    # load the data
    data = pd.read_csv(path, index_col=0)
    if as_timedelta:
        convert_to_timedelta(data)
    logging.debug(f"Loaded DataFrame from {path}")
    return profile_type, data


def write_timedelta(d: timedelta | None) -> str | None:
    """
    Converts a timedelta into a str. Necessary to correctly
    represent None as null in json.

    :param d: timedelta to write
    :return: str representation of the timedelta
    """
    return str(d) if d else None


def parse_timedelta(s: str) -> timedelta:
    """
    Parses a timedelta object from a string. Only supports a
    resolution up to seconds.

    :param s: the string to parse the timedelta from
    :return: parsed timedelta object
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

    def expand(self) -> list[str]:
        """
        Provides this activity in expanded format: a list of fixed length
        time slots with the same code, corresponding to the duration of the
        activity.

        :return: activity in expanded format
        """
        return [self.name] * self.duration

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


@dataclass_json
@dataclass
class SparseActivityProfile:
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
        path: Path | str,
        profile_type: ProfileType,
        resolution: timedelta = DEFAULT_RESOLUTION,
    ) -> "SparseActivityProfile":
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
        profile = SparseActivityProfile(entries, offset, resolution, profile_type)
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

    def expand(self) -> list[str]:
        """
        Provides this activity profile in expanded format.

        :return: expanded activity profile
        """
        profile = list(
            itertools.chain.from_iterable(a.expand() for a in self.activities)
        )
        assert len(profile) == self.length()
        return profile

    @utils.timing
    def apply_activity_mapping(self, activity_mapping: dict[str, str]) -> None:
        """
        Maps all activity names according to the provided dict.

        :param activity_mapping: the activity name mapping to use
        """
        for activity in self.activities:
            activity.name = activity_mapping[activity.name]
        # TODO: should consecutive activities that were mapped to the same name
        # be merged? Would be more similar to HETUS data.

    @utils.timing
    def resample(self, resolution: timedelta) -> None:
        """
        Resamples this activity profile to a decreased resolution.
        Only permits new resolutions that are an integer multiple of
        the current one.

        :param resolution: the target resolution
        """
        assert resolution % self.resolution == timedelta(0) and timedelta(
            1
        ) % resolution == timedelta(0), (
            f"Invalid target resolution: {resolution}. The target resolution "
            "must be a divisor of one day and an integer multiple of the "
            "current resolution"
        )
        assert self.start() == 0, "Timesteps must start at 0 for resampling"
        original_length = len(self.activities)
        # determine length of time frame that will be merged
        # into a single timestep with the new resolution
        frame_length = int(resolution / self.resolution)
        # determine the new end timestep (must be a multiple of frame_length)
        end = self.length() // frame_length * frame_length
        index = 0
        new_activities: list[ActivityProfileEntry] = []
        # iterate through all time frames to merge their activities
        for frame_start in range(0, end, frame_length):
            frame_end = frame_start + frame_length
            # collect all activities intersecting the current time frame
            activities: list[ActivityProfileEntry] = [self.activities[index]]
            while activities[-1].end() < frame_end:
                index += 1
                assert index < len(
                    self.activities
                ), "The last incomplete frame is discared, so this should not happen"
                activities.append(self.activities[index])
            if activities[-1].end() == frame_end:
                # this activity ends in this frame and is not
                # relevant anymore for the next one
                index += 1
            # determine which activity receives the time frame
            if len(activities) == 1:
                if len(new_activities) == 0 or activities[0] is not new_activities[-1]:
                    new_activities.append(activities[0])
                continue
            # find activity with largest time share in this time frame
            d = [a.duration for a in activities]
            # subtract duration share outside of this time frame
            d[0] -= frame_start - activities[0].start
            d[-1] -= activities[-1].end() - frame_end
            # find activity with max duration, it will fill the whole frame
            longest_act = activities[np.argmax(d)]
            # adapt start/duration of this activity
            new_start = min(longest_act.start, frame_start)
            new_end = max(longest_act.end(), frame_end)
            longest_act.start = new_start
            longest_act.duration = new_end - new_start
            # delete or adapt other activities accordingly
            first = activities[0]
            last = activities[-1]
            if first is not longest_act and first.start < frame_start:
                # make activity end before this frame
                first.duration = frame_start - first.start
            if last is not longest_act and last.end() > frame_end:
                # make activity start after this frame
                test = last.end()
                last.duration -= frame_end - last.start
                last.start = frame_end
            # add the 'winning' activity to the new list, if it is not
            # in there yet
            if len(new_activities) == 0 or longest_act is not new_activities[-1]:
                new_activities.append(longest_act)

        # the duration of the last activity might be too long
        if new_activities[-1].end() != end:
            new_activities[-1].duration = end - new_activities[-1].start

        # adapt timestep count of the new activities
        for a in new_activities:
            assert a.start % frame_length == 0, "Bug in resampling"
            assert a.duration % frame_length == 0, "Bug in resampling"
            a.start //= frame_length
            a.duration //= frame_length
        # check if new activity list is valid
        for i in range(len(new_activities) - 1):
            assert (
                new_activities[i].end() == new_activities[i + 1].start
            ), "Bug in resampling"
        # assign the new resolution and activity list
        self.activities = new_activities
        self.resolution = resolution
        deleted_activities = original_length - len(new_activities)
        logging.info(
            f"Resampled activity profile, deleting {deleted_activities} activities"
        )

    @utils.timing
    def split_into_day_profiles(
        self,
        split_offset: timedelta = hetus_constants.PROFILE_OFFSET,
    ) -> list["SparseActivityProfile"]:
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

        day_profiles: list[SparseActivityProfile] = []
        current_day_profile: list[ActivityProfileEntry] = []
        for activity in self.activities:
            if activity.end() >= next_split:
                # the activity lasts over the specified day switch time
                split_sections = activity.split(next_split, timesteps_per_day)
                assert len(split_sections) > 0, "Invalid split"
                # add the profile for the past day
                current_day_profile.append(split_sections[0])
                day_profiles.append(
                    SparseActivityProfile(
                        current_day_profile,
                        split_offset,
                        self.resolution,
                        self.profile_type,
                    )
                )
                # add intermediate 24 h split sections as separate profile
                day_profiles.extend(
                    SparseActivityProfile(
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


class ExpandedActivityProfiles:
    """
    Contains multiple activity profiles in expanded format (HETUS-like)
    of one category
    """

    def __init__(
        self,
        data: pd.DataFrame,
        profile_type: ProfileType,
        offset: timedelta,
        resolution: timedelta,
    ) -> None:
        self.data = data
        self.profile_type = profile_type
        self.offset = offset
        self.resolution = resolution

    @utils.timing
    @staticmethod
    def from_sparse_profiles(profiles: list[SparseActivityProfile]):
        """
        Converts a list of activity profiles from sparse to expanded
        format. Stores all profiles in a single object. All profiles
        must be of the same category.

        :param profiles: list of sparse profiles to convert
        :return: profile set in expanded format
        """
        offset = profiles[0].offset
        profile_type = profiles[0].profile_type
        resolution = profiles[0].resolution
        # check that all profiles have the same properties
        assert all(
            p.offset == offset for p in profiles
        ), "Profiles have different offsets"
        assert all(
            p.profile_type == profile_type for p in profiles
        ), "Profiles have different profile types"
        assert all(
            p.resolution == resolution for p in profiles
        ), "Profiles have different resolution"
        # expand the profiles
        rows = [p.expand() for p in profiles]
        length = len(rows[0])
        assert all(
            len(row) == length for row in rows
        ), "Profiles have different lengths"
        column_names = [f"Timestep {i}" for i in range(1, length + 1)]
        data = pd.DataFrame(rows, columns=column_names)
        return ExpandedActivityProfiles(data, profile_type, offset, resolution)

    @utils.timing
    def create_sparse_profiles(self) -> list[SparseActivityProfile]:
        """
        Converts this set of activity profiles from expanded to sparse
        format, i.e. each activity is represented by a single
        activity profile entry object instead of a list of successive
        time slots.

        :return: list of activity profiles in sparse format
        """
        profiles: list[SparseActivityProfile] = []
        # iterate through all diary entries
        for index, row in self.data.iterrows():
            entries = []
            start = 0
            # iterate through groups of consecutive slots with the same code
            for code, group in itertools.groupby(row):
                l = list(group)
                length = len(l)
                entries.append(ActivityProfileEntry(code, start, length))
                start += length
            # create ActivityProfile objects out of the activity entries
            profiles.append(
                SparseActivityProfile(
                    entries,
                    self.offset,
                    self.resolution,
                    self.profile_type,
                )
            )
        return profiles


@dataclass_json
@dataclass
class HHActivityProfiles:
    """
    Bundles the activity profiles from all people in one household
    """

    activity_profiles: dict[str, SparseActivityProfile] = field(default_factory=dict)

    household: str | None = None
