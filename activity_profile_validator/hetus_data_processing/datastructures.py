"""
Defines classes for activity profiles
"""

from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config


# TODO: does not work for some reason
# dataclasses_json.cfg.global_config.encoders[timedelta] = str
# dataclasses_json.global_config.decoders[timedelta] =


def parse_timedelta(s: str) -> timedelta:
    """
    Parses a timedelta object from a string. Does not
    support timedeltas >= 24 h, and only supports hours,
    minutes and seconds.

    :param s: the string to parse the timedelta from
    :type s: str
    :return: parsed timedelta object
    :rtype: timedelta
    """
    t = datetime.strptime(s, "%H:%M:%S")
    return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)


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
        default=None, metadata=config(encoder=str, decoder=parse_timedelta)
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
    activities: List[ActivityProfileEntry]

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
