"""
Constants for working with the HETUS 2010 data set.
"""

from datetime import timedelta

#: length of each activity time slot in minutes
RESOLUTION = timedelta(minutes=10)
#: in HETUS 2010, only Austria uses 15 minute time slots
RESOLUTION_AT = timedelta(minutes=15)

#: the start time of each diary, as offset from 00:00
PROFILE_OFFSET = timedelta(hours=4)

# Requirements from Eurostat to permit publication of the dataset.
# source: https://ec.europa.eu/eurostat/product?code=KS-RA-08-014
#: minimum number of people per group
MIN_CELL_SIZE = 20
#: minimum group size to disclose exact group size
MIN_CELL_SIZE_FOR_SIZE = 50


def get_resolution(country: str | None) -> timedelta:
    """
    Returns the correct HETUS time slot resolution depending
    on the country.

    :param country: the country code (e.g. 'DE')
    :return: the resolution of the records of that country
    """
    return RESOLUTION if country != "AT" else RESOLUTION_AT
