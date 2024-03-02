"""
Defines classes for activity profiles
"""

from datetime import datetime, time, timedelta
import itertools
import logging
from pathlib import Path
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from activity_validator.hetus_data_processing import hetus_constants
from activity_validator.profile_category import ProfileCategory
from activity_validator import utils


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
        The activity has to start before first_split, but may end exactly at it.

        :return: the list of activity entries
        """
        assert (
            self.start < first_split <= self.end()
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


@dataclass
class SparseActivityProfile:
    """
    Class for storing a single activity profile, of a single person
    on a single day.
    """

    #: list of activity objects
    activities: list[ActivityProfileEntry]
    #: time offset from midnight
    offset: timedelta
    #: duration of one timestep
    resolution: timedelta
    #: characteristics of the person this profile belongs to
    profile_type: ProfileCategory = field(default_factory=ProfileCategory)
    #: name of the file this profile was loaded from, if applicable (for debugging)
    filename: str = ""

    @utils.timing
    @staticmethod
    def load_from_csv(
        path: Path,
        profile_type: ProfileCategory,
        resolution: timedelta,
        offset: timedelta | None = None,
    ) -> "SparseActivityProfile":
        """
        Loads an ActivityProfile from a csv file.

        :param path: path to the csv file
        :param timestep: timestep resolution of the profile, defaults to DEFAULT_RESOLUTION
        :param offset: timedelta from 00:00 of the first day to the start time of the first
                       activity; can be omitted if a 'Date' column is contained
        :return: the loaded ActivityProfile
        """
        assert timedelta(days=1) % resolution == timedelta(
            0
        ), "Resolution has to be a divisor of 1 day"
        # define column names
        timestep_col = "Timestep"
        date_col = "Date"
        activity_col = "Activity"
        data = pd.read_csv(path)
        entries = data.apply(  # type: ignore
            lambda row: ActivityProfileEntry(row[activity_col], row[timestep_col]),
            axis=1,
        ).to_list()
        if offset is None:
            # calculate offset (timedelta since last midnight)
            first_date = datetime.fromisoformat(data[date_col][0])
            offset = first_date - datetime.combine(first_date.date(), time())
        assert offset % resolution == timedelta(
            0
        ), "Start time has to be a divisor of the resolution"
        profile = SparseActivityProfile(entries, offset, resolution, profile_type)
        profile.remove_timestep_offset()
        profile.calc_durations()
        # remove the last activity (duration is unknown)
        profile.activities.pop()
        profile.filename = path.name
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

    def is_last_and_first_same(self) -> bool:
        """
        Returns True, if the first and the last activity of the profile
        are the same. For daily profiles, this can be used to indicate
        activities like 'sleep' that continue over the day transition
        time.

        :return: whether first and last activity are the same
        """
        return self.activities[0].name == self.activities[-1].name

    def get_merged_activity_list(self) -> list[ActivityProfileEntry]:
        """
        Returns a list of activities, in which the first and last activity
        have been merged, if they were the same. The new activity list starts
        and ends later than the original one, but has the same duration.
        Other activities besides the first and last are unaffected.

        :return: the merged activitiy list
        """
        if not self.is_last_and_first_same() or len(self.activities) == 1:
            # only one activity or first and last activity are different - nothing to adapt
            return self.activities
        # merge the first and last activity to one activity
        first, last = self.activities[0], self.activities[-1]
        merged = ActivityProfileEntry(
            first.name, last.start, first.duration + last.duration
        )
        # remove the original first and last activity, and append the merged one
        activities = self.activities[1:-1] + [merged]
        return activities

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

    @staticmethod
    def merge_activities(
        first: ActivityProfileEntry, last: ActivityProfileEntry
    ) -> ActivityProfileEntry:
        """
        Merges a range of consecutive activities.

        :param first: the first activity in the range
        :param last: the last activity in the range
        :return: a new activity object encompassing the whole range
        """
        assert (
            first.name == last.name
        ), f"Cannnot merge different activities: {first.name} and {last.name}"
        dur = last.end() - first.start
        return ActivityProfileEntry(first.name, first.start, dur)

    def join_adjacent_activities(self) -> None:
        """
        Joins consecutive activities of the same name. This is e.g. necessary after
        applying an activity mapping to treat this data the same as expanded
        activity profiles.
        """
        start = 0
        activities = []
        for i, a in enumerate(self.activities[1:]):
            if a.name != self.activities[start].name:
                # i starts at 0, so the index of a is i+1
                if i == start:
                    # activity remains unchanged
                    activities.append(self.activities[start])
                else:
                    # multiple activities with same name - merge
                    activities.append(
                        SparseActivityProfile.merge_activities(
                            self.activities[start], self.activities[i]
                        )
                    )
                start = i + 1
        # add the last activity
        if start == len(self.activities) - 1:
            activities.append(self.activities[start])
        else:
            activities.append(
                SparseActivityProfile.merge_activities(
                    self.activities[start], self.activities[-1]
                )
            )
        assert (
            self.activities[0].start == activities[0].start
        ), "Bug in activity joining: wrong start"
        assert (
            self.activities[-1].end() == activities[-1].end()
        ), "Bug in activity joining: wrong end"
        for i, a in enumerate(activities[:-1]):
            assert (
                a.end() == activities[i + 1].start
            ), "Bug in activity joining: start/end don't match"
        self.activities = activities

    @utils.timing
    def apply_activity_mapping(self, activity_mapping: dict[str, str]) -> None:
        """
        Maps all activity names according to the provided dict.

        :param activity_mapping: the activity name mapping to use
        """
        for activity in self.activities:
            activity.name = activity_mapping[activity.name]
        self.join_adjacent_activities()

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
        assert (
            self.length() >= frame_length
        ), "The profile is too short for resampling to the target resolution"
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
        assert split_offset % self.resolution == timedelta(
            0
        ), f"Invalid split offset: {split_offset}"
        timesteps_per_day = int(timedelta(days=1) / self.resolution)
        # calculate timestep of first split
        next_split = int((split_offset - self.offset) / self.resolution)
        if next_split <= 0:
            # first split is on the next day
            next_split += timesteps_per_day

        day_profiles: list[SparseActivityProfile] = []
        current_day_profile: list[ActivityProfileEntry] = []
        for activity in self.activities:
            if activity.end() >= next_split:
                # the activity lasts over or until the specified day switch time
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
                if (activity.end() - next_split) % timesteps_per_day == 0:
                    # activity ends just on a day split timestep
                    current_day_profile = []
                    days_passed = len(split_sections)
                    last_full_day = None
                else:
                    # add the last section to the list for the following day
                    current_day_profile = [split_sections[-1]]
                    days_passed = len(split_sections) - 1
                    last_full_day = -1
                # increment the timestep for the next split
                next_split += timesteps_per_day * days_passed
                # add intermediate 24 h split sections as separate profile
                day_profiles.extend(
                    SparseActivityProfile(
                        [a],
                        split_offset,
                        self.resolution,
                        self.profile_type,
                    )
                    for a in split_sections[1:last_full_day]
                )
            else:
                # the activity does not need to be split
                current_day_profile.append(activity)
        return day_profiles


class ExpandedActivityProfiles:
    """
    Contains multiple activity profiles in expanded format (HETUS-like)
    of one category
    """

    def __init__(
        self,
        data: pd.DataFrame,
        profile_type: ProfileCategory,
        offset: timedelta,
        resolution: timedelta,
    ) -> None:
        self.data = data
        self.profile_type = profile_type
        self.offset = offset
        self.resolution = resolution

    def get_profile_count(self) -> int:
        """
        Returns the number of contained activity profiles

        :return: number of activity profiles
        """
        return len(self.data)

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
                length = len(list(group))
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
