"""
Defines classes for activity profiles
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config


# TODO: does not work for some reason
# dataclasses_json.cfg.global_config.encoders[timedelta] = str
# dataclasses_json.global_config.decoders[timedelta] =


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
    #: 0-based index of activity start
    start: datetime
    #: duration of activity in time steps
    duration: Optional[timedelta] = field(
        default=None,
        metadata=config(encoder=write_timedelta, decoder=parse_timedelta),
    )


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
    activities: List[ActivityProfileEntry | ActivityProfileEntryTime]

    person: Optional[str] = None
    daytype: Optional[str] = None

    def calc_durations(self, profile_end=None) -> None:
        """
        Calculates and sets the duration for each contained activity.

        :param profile_end: the end of the whole profile, necessary
                            for calculating the duration of the last
                            activity
        """
        assert self.activities, "Empty activity list"
        for i, a in enumerate(self.activities[:-1]):
            assert a.duration is None
            a.duration = self.activities[i + 1].start - a.start
        if profile_end is not None:
            # if the overall end is specified, the duration of the last
            # activity can be calculated
            last_activity = self.activities[-1]
            last_activity.duration = profile_end - last_activity.start


@dataclass_json
@dataclass
class HHActivityProfiles:
    """
    Bundles the activity profiles from all people in one household
    """

    activity_profiles: Dict[str, ActivityProfile] = field(default_factory=dict)

    household: Optional[str] = None
