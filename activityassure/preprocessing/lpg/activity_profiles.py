"""
Loads activity profiles from the result database files of the LoadProfileGenerator
and creates csv files from them that can be used in the validation framework.
Also generates a preliminary activity mapping in the process using the activity
categories defined in the LoadProfileGenerator. Some categories cannot be
assigned an activity unambiguously, so the mapping file needs to be checked
and completed manually afterwards.
If a mapping file already exists, it is loaded and expanded if necessary.
"""

from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import sqlite3

import pandas as pd

from activityassure import activity_mapping

from activityassure.preprocessing.lpg import person_characteristics


#: used as a placeholder for ambiguous categories
UNMAPPED_CATEGORY = "TODO"
#: preliminary affordance mappings according to affordance categories
CATEGORY_MAPPING = {
    "Active Entertainment (Computer, Internet etc)": "pc",
    "Entertainment": UNMAPPED_CATEGORY,
    "Office": "work",
    "Offline Entertainment": "other",
    "Outside recreation": "not at home",
    "Passive Entertainment (TV etc.)": UNMAPPED_CATEGORY,
    "child care": "other",
    "cleaning": UNMAPPED_CATEGORY,  # laundry is separate
    "cooking": "cook",
    "gardening and maintenance": "other",
    "hygiene": "personal care",
    "other": "other",
    "school": "education",
    "shopping": "not at home",
    "sleep": "sleep",
    "sports": UNMAPPED_CATEGORY,
    "work": "work",
}
#: Mappings for affordances that start with a certain prefix. These are
#  usually auto-generated affordances.
AFFORDANCE_PREFIX_MAPPING = {
    "travel on ": "travel",
    "Idleness for ": "idle",
}


def load_activity_profile_from_db(
    database_file: Path, mapping_path: Path
) -> dict[str, pd.DataFrame]:
    """
    Converts LPG activity profiles to the target csv format.
    Also creates or extends the LPG activity mapping file.

    :param db_file: the database file to load
    :param mapping_path: path to the affordance mapping file
    """
    assert database_file.is_file(), f"Database file not found: {database_file}"

    # load activity mapping
    if mapping_path.is_file():
        # load the existent mapping to extend it
        mapping = activity_mapping.load_mapping(mapping_path)
    else:
        # initialize a new mapping
        mapping = {}

    # get all activities from LPG result database
    con = sqlite3.connect(str(database_file))
    with con:
        cur = con.cursor()
        query = "SELECT * FROM PerformedActions"
        results = cur.execute(query)
        activity_list: list[tuple[str, str]] = results.fetchall()
    # parse the json info column for each activity
    parsed_json_list = [json.loads(act) for name, act in activity_list]
    # the list contains activities of all persons, so they need to be grouped
    rows_by_person: dict[str, list[tuple[int, datetime, str]]] = defaultdict(list)
    unmapped_affordances = {}
    for entry in parsed_json_list:
        start_date = datetime.fromisoformat(entry["DateTime"])
        affordance: str = entry["AffordanceName"]
        category = entry["Category"]
        # check if the action was traveling
        for prefix, mapped_category in AFFORDANCE_PREFIX_MAPPING.items():
            if affordance.startswith(prefix):
                # The affordance matches the pattern, use the specified category.
                # Also overwrite the affordance name, as the auto-generated travel/idleness
                # affordance names are not useful.
                affordance = mapped_category
                category = mapped_category
                break
        # check for unmapped affordances
        if affordance not in mapping and affordance not in unmapped_affordances:
            unmapped_affordances[affordance] = CATEGORY_MAPPING.get(
                category, UNMAPPED_CATEGORY
            )
        # store the relevant information for each activity
        person = entry["PersonName"]
        start_step = entry["TimeStep"]["ExternalStep"]
        activity_entry = (start_step, start_date, affordance)
        rows_by_person[person].append(activity_entry)

    if unmapped_affordances:
        print(f"Found {len(unmapped_affordances)} unmapped affordances")
        merged = mapping | unmapped_affordances
        with open(mapping_path, "w", encoding="utf8") as f:
            # add unmapped affordances to mapping file
            json.dump(merged, f, indent=4)

    # store the activities in one DataFrame per person
    profiles = {
        person: pd.DataFrame(rows, columns=["Timestep", "Date", "Activity"])
        for person, rows in rows_by_person.items()
    }
    return profiles


def convert_activity_profile_from_db_to_csv(
    db_file: Path, result_dir: Path, mapping_path: Path, id: str, template: str = ""
):
    """
    Loads a single LPG result database file and converts the contained activity
    profiles to csv files. Writes any new, still uncategorized affordances into the
    mapping file.

    :param raw_data_dir: LPG result directory containing the database file
    :param result_dir: output folder for the created csv files
    :param hh_key: household key of the file to load, defaults to "HH1"

    :param db_file: the database file to load
    :param result_dir: the result directory to store the csv files
    :param id: ID of the calculation to distinguish results for the same template
    :param template: the household template name
    """
    # get the profiles as dataframes
    profile_per_person = load_activity_profile_from_db(db_file, mapping_path)

    # store each dataframe as a csv file
    result_dir.mkdir(parents=True, exist_ok=True)
    for person, data in profile_per_person.items():
        # LPG person name pattern: "CHR01 Sami (25/Male)"
        person_name = person.split(" (")[0]
        if template:
            # template was externally set, compare it to the person name
            person_id = person_characteristics.get_person_id(person_name, template)
        else:
            person_id = person_name
        result_path = result_dir / f"{person_id}_{id}.csv"
        data.to_csv(result_path)
