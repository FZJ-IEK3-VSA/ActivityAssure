"""
Constants for working with HETUS data. 
"""

from datetime import timedelta

#: lenght of each activity time slot in minutes
RESOLUTION = timedelta(minutes=10)
#: in HETUS 2010, only Austria uses 15 minute time slots
RESOLUTION_AT = timedelta(minutes=15)

#: the start time of each diary
PROFILE_OFFSET = timedelta(hours=4)


def get_resolution(country: str | None) -> timedelta:
    """
    Returns the correct HETUS time slot resolution depending
    on the country.

    :param country: the country code (e.g. 'DE')
    :return: the resolution of the records of that country
    """
    return RESOLUTION if country != "AT" else RESOLUTION_AT
