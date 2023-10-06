"""Main module"""

import os
from typing import Dict, List

import pandas as pd

from activity_profile_validator.hetus_data_processing.datastructures import (
    ActivityProfileEntryTime,
    ActivityProfile,
)

def load_activity_profiles(dir: str) -> List[ActivityProfile]:
    """Loads the activity profiles in json format from the specified folder"""
    activity_profiles = []
    for filename in os.listdir(dir):
        path = os.path.join(dir, filename)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                file_content = f.read()
                activity_profile = ActivityProfile.from_json(file_content)
                activity_profiles.append(activity_profile)
    return activity_profiles


def map_templates_to_hetus_households():
    pass


def validation():
    pass
