"""
Constants for working with HETUS data. 
"""

from datetime import timedelta

#: lenght of each activity time slot in minutes
MIN_PER_TIME_SLOT = 10
#: in HETUS 2010, only Austria uses 15 minute time slots
MIN_PER_TIME_SLOT_AT = 15

#: the start time of each diary
PROFILE_OFFSET = timedelta(hours=4)
