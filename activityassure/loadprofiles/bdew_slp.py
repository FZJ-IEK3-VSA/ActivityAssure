"""Loads BDEW standard load profiles and provides the adapted profile for specific days."""

from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
import holidays
import pandas as pd

#: path to the BDEW standard load profile file
#  This file is available for download here: https://www.bdew.de/energie/standardlastprofile-strom/
BDEW_PROFILE_PATH = Path(
    "data/load_profiles/Repräsentative_Profile_BDEW_H25_G25_L25_P25_S25_Veröffentlichung.xlsx"
)


class BDEWProfile(StrEnum):
    """Standard load profiles provided by the BDEW"""

    HOUSEHOLD = "H25"
    COMMERCIAL = "G25"
    AGRICULTURE = "L25"
    COMBINATION_PV = "P25"
    COMBINATION_STORAGE_PV = "S25"


class DayType(StrEnum):
    """Possible day types for the BDEW standard load profiles."""

    WEEKDAY = "WT"
    SATURDAY = "SA"
    HOLIDAY = "FT"


def dynamization_factor(t: int) -> float:
    """
    Dynamization factor that needs to be applied to each value of the H25 standard load profile
    to adapt it to the desired date (source: see BDEW reference above).

    :param t: day index of the year (1-365, 366 for leap years)
    :return: the factor to apply to the H25 profile values
    """
    return -3.92e-10 * t**4 + 3.20e-7 * t**3 - 7.02e-5 * t**2 + 2.10e-3 * t + 1.24


def load_bdew_profile(profile: BDEWProfile = BDEWProfile.HOUSEHOLD):
    """
    Loads a BDEW standard load profile from the Excel file.
    The file can be downloaded from the BDEW website and must be placed
    in the `data/load_profiles` directory.

    :param profile: the profile to load, defaults to BDEWProfile.HOUSEHOLD
    :return: the requested raw profile
    """
    assert BDEW_PROFILE_PATH.is_file(), (
        "BDEW profile file not found. Please download it from "
        "https://www.bdew.de/energie/standardlastprofile-strom/ and place it in the "
        "'data/load_profiles' directory."
    )

    # Load the sheet while skipping the first two irrelevant rows
    df = pd.read_excel(
        BDEW_PROFILE_PATH,
        sheet_name=profile,
        header=[2, 3],  # Use row 3 and 4 for a MultiIndex header
    )

    # extract the second column to parse the time index from it
    timecol = df.iloc[:, 1]
    # Extract the start time from each time range string
    start_times = timecol.str.extract(r"(\d{2}:\d{2})")[0]

    # remove the first two columns (first is empty, second is extracted as time index)
    df = df.drop(columns=df.columns[:2])

    # Assign the extracted time as index
    df.index = pd.to_datetime(start_times, format="%H:%M").dt.time  # type: ignore

    # rebuild the MultiIndex to make the sure dropped columns are not included
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    # the first column index level actually contains dates; select only the month index
    df.columns = df.columns.set_levels(df.columns.levels[0].month, level=0)  # type: ignore

    # Optional: reset column names to simpler format if needed
    # df.columns = [f"{month}_{daytype}" for month, daytype in df.columns]
    return df


class BDEWProfileProvider:
    """
    Provides adapted BDEW standard load profiles for specific days.
    All provided profiles contain electricity demand in kWh at 15-minute intervals.
    The time stamp for each value indicates the start time of the 15-minute interval.
    """

    def __init__(self, profile_type: BDEWProfile = BDEWProfile.HOUSEHOLD) -> None:
        self.profile_type = profile_type
        self.profiles = load_bdew_profile(profile_type)

    def get_profile_for_day(self, day: date, country: str = "DE") -> pd.Series:
        """
        Get the adapted BDEW profile for a specific day of the year.

        :param profile: The BDEW profile type to load.
        :param day: the date to get the profile for (relevant for day of year)
        :param country: the country to check for holidays (default: "DE" for Germany)
        """
        # load the BDEW profile
        df = self.profiles

        # determine the correct day profile to use
        day_type = DayType.WEEKDAY
        if day in holidays.country_holidays(country) or day.weekday() == 6:
            # holiday or sunday
            day_type = DayType.HOLIDAY
        elif day.weekday() == 5:
            day_type = DayType.SATURDAY

        raw_profile = df[(day.month, str(day_type))]

        # apply the dynamisation factor
        day_of_year = day.timetuple().tm_yday
        factor = dynamization_factor(day_of_year)
        adapted_profile = raw_profile * factor

        # adapt the index to include the date instead of just the time
        adapted_profile.index = pd.DatetimeIndex(
            [datetime.combine(day, t) for t in adapted_profile.index]
        )
        return adapted_profile

    def get_profile_for_date_range(
        self, start: date, end: date, country: str = "DE"
    ) -> pd.Series:
        """
        Get the combined BDEW day profiles for a range of dates.

        :param start: the start date of the range
        :param end: the end date of the range (inclusive)
        :param country: the country to check for holidays (default: "DE" for Germany)
        """
        profiles = []
        current_date = start
        while current_date <= end:
            daily_profile = self.get_profile_for_day(current_date, country)
            profiles.append(daily_profile)
            current_date += pd.Timedelta(days=1)
        return pd.concat(profiles)  # type: ignore
