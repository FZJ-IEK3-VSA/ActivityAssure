"""
Loads activity profiles from the result database files of the LoadProfileGenerator
and creates csv files from them that can be used in the validation framework.
Also generates a preliminary activity mapping in the process using the activity
categories defined in the LoadProfileGenerator. Some categories cannot be
assigned an activity unambiguously, so the mapping file needs to be checked
and completed manually afterwards.
If a mapping file already exists, it is loaded and expanded if necessary.
"""

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from activityassure import activity_mapping, utils
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

# special targets; travel related to these targets is categorized with the same category
SPECIAL_TARGETS = {"work", "education"}


def get_travel_activity_type(
    act_type_before: str, act_type_after: str, to_home: bool
) -> str:
    """Checks whether the travel is related to a special affordance, and
    depending on that returns the activity type that should be used in the
    validation.

    :param act_type_before: activity type before the travel
    :param act_type_after:  activity type after the travel
    :param to_home: whether the travel leads towards Home
    :return: the activity type to use
    """
    # return True if the travel leads to a special target, or comes from a special target
    # towards home
    if act_type_after in SPECIAL_TARGETS:
        return act_type_after
    if act_type_before in SPECIAL_TARGETS and to_home:
        return act_type_before
    return "travel"


def adapt_travel_affordance(
    before: str, after: str, to_home: bool, mapping: dict[str, str]
) -> tuple[str, bool]:
    """Special handling for travels: checks whether the travel is
    related to some specific purposes, and if so, sets a new specific
    affordance name. If necessary, updates the affordance mapping.

    Remark: this is necessary for consistent validation because the HETUS mapping
    assigns the work/education activity category to travels related to that
    purpose (see activityassure/activities/mapping_hetus.json).

    :param before: name of the affordance before the travel
    :param after: name of the affordance after the travel
    :param to_home: whether the travel leads towards Home
    :param mapping: the affordance mapping
    :return: the travel affordance name to use, and a bool whether it was missing in
             the affordance mapping
    """
    # get the respective affordance types
    activity_type = mapping.get(before, "")
    activity_type = mapping.get(after, "")
    travel_cat = get_travel_activity_type(activity_type, activity_type, to_home)
    affordance = "travel" if travel_cat == "travel" else f"travel for {travel_cat}"
    # add the special affordance to the mapping, if necessary
    not_in_mapping = affordance not in mapping
    if not_in_mapping:
        mapping[affordance] = travel_cat
    return affordance, not_in_mapping


def load_lpg_result_table_sql(database_file: Path, table: str) -> list[dict]:
    """
    Loads the specified table from the sqlite database and returns the parsed
    JSON as a list of dicts.

    :param database_file: path of the database file to load
    :param table: name of the table to load
    :return: parsed JSON content of all items
    """
    assert database_file.is_file(), f"Database file not found: {database_file}"
    # get all items from an LPG result database
    con = sqlite3.connect(str(database_file))
    with con:
        cur = con.cursor()
        query = f"SELECT * FROM {table}"
        results = cur.execute(query)
        activity_list: list[tuple[str, str]] = results.fetchall()
    # parse the json info column for each row
    parsed_json_list = [json.loads(content) for name, content in activity_list]
    return parsed_json_list


def load_lpg_result_table_json(database_dir: Path, table: str) -> list[dict]:
    """Loads the specified table from the JSON directory database and returns
    the parsed JSON of the 'Json' column as a list of dicts.

    :param database_file: path of the database file to load
    :param table: name of the table to load
    :return: parsed JSON content of all items
    """
    assert database_dir.is_dir(), f"Database directory not found: {database_dir}"
    table_file = database_dir / f"{table}.json"
    assert table_file.is_file(), f"Database table file not found: {table_file}"
    with open(table_file, "r", encoding="utf8") as f:
        data = json.load(f)
    parsed_json_list = [json.loads(d["Json"]) for d in data]
    return parsed_json_list


def load_lpg_result_table(database_path: Path, table: str) -> list[dict]:
    """Automatically loads an LPG result table in the given format (sql or JSON).

    :param database_path: path of the database (file or directory) to load
    :param table: name of the table to load
    :return: parsed JSON content of all items
    """
    if database_path.suffix == ".sqlite":
        parsed_json_list = load_lpg_result_table_sql(database_path, table)
    elif database_path.is_dir():
        parsed_json_list = load_lpg_result_table_json(database_path, table)
    else:
        assert False, f"Unknown database format: {database_path}"
    return parsed_json_list


def load_activity_profiles_from_db(
    database_path: Path, mapping_path: Path
) -> dict[str, pd.DataFrame]:
    """
    Converts LPG activity profiles to the target csv format.
    Also creates or extends the LPG activity mapping file.

    :param db_file: the database file to load
    :param mapping_path: path to the affordance mapping file
    :returns: a dict containing one activity profile per person
    """
    # load activity data depending on the database format
    activity_table = "PerformedActions"
    parsed_json_list = load_lpg_result_table(database_path, activity_table)

    # load activity mapping
    if mapping_path.is_file():
        # load the existent mapping to extend it
        mapping = activity_mapping.load_mapping(mapping_path)
    else:
        # initialize a new mapping
        mapping = {}

    # the list contains activities of all persons, so they need to be grouped
    entries_by_persons: dict[str, list[dict]] = defaultdict(list)
    for entry in parsed_json_list:
        person = entry["PersonName"]
        entries_by_persons[person].append(entry)

    rows_by_person: dict[str, list[tuple[int, datetime, str]]] = defaultdict(list)
    unmapped_affordances = {}
    unmapped_affordances = 0
    for person, entries in entries_by_persons.items():
        for i, entry in enumerate(entries):
            start_date = datetime.fromisoformat(entry["DateTime"])
            affordance: str = entry["AffordanceName"]
            category = entry["Category"]
            # check if the action name needs to be generalized, e.g., for traveling
            for prefix, mapped_category in AFFORDANCE_PREFIX_MAPPING.items():
                if affordance.startswith(prefix):
                    # The affordance matches the pattern, use the specified category.
                    # Also overwrite the affordance name, as the auto-generated travel/idleness
                    # affordance names are not useful.
                    affordance = mapped_category
                    category = mapped_category
                    break

            # special case for work- or education-related travel
            if affordance == "travel":
                # get previous and next affordance names
                before = entries[i - 1]["AffordanceName"] if i > 0 else ""
                after = entries[i + 1]["AffordanceName"] if i < len(entries) - 1 else ""
                to_home = "to Home" in entry["AffordanceName"]
                # check whether to use the generic "travel" affordance or a more specific one
                new_aff, unmapped = adapt_travel_affordance(
                    before, after, to_home, mapping
                )
                if new_aff != affordance:
                    affordance = new_aff
                if unmapped:
                    unmapped_affordances += 1

            # check for unmapped affordances
            if affordance not in mapping:
                mapping[affordance] = CATEGORY_MAPPING.get(category, UNMAPPED_CATEGORY)
                unmapped_affordances += 1

            # store the relevant information for each activity
            start_step = entry["TimeStep"]["ExternalStep"]
            activity_entry = (start_step, start_date, affordance)
            rows_by_person[person].append(activity_entry)

    if unmapped_affordances > 0:
        print(f"Found {unmapped_affordances} unmapped affordances")
        with open(mapping_path, "w", encoding="utf8") as f:
            # add unmapped affordances to mapping file
            json.dump(mapping, f, indent=4)

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

    :param db_file: the database file to load
    :param result_dir: the result directory to store the csv files
    :param mapping_path: the activity mapping file to use
    :param id: ID of the calculation to distinguish results for the same template
    :param template: the household template name
    """
    # get the profiles as dataframes
    profile_per_person = load_activity_profiles_from_db(db_file, mapping_path)

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


@utils.timing
def convert_activity_profiles(
    hh_dbs: dict[str, Path], result_dir: Path, mapping_path: Path
):
    """
    Converts all activity profiles generated in an LPG City Simulation to CSV files.

    :param hh_dbs: dictionary with IDs and paths to all household database files
    :param result_dir: result directory to save the activity profiles to
    :param mapping_path: path to the activity mapping file to use
    """
    result_dir.mkdir(parents=True, exist_ok=True)
    # the Houses directory contains one subdirectory per house
    for hh_id, db_file in hh_dbs.items():
        convert_activity_profile_from_db_to_csv(
            db_file, result_dir, mapping_path, hh_id
        )


def collect_household_dbs(result_dir: Path) -> dict[str, Path]:
    """
    Collects all household result databases from a city simulation. The
    databases are either sqlite files or directories of JSON files, depending
    on which output format was used in the LPG.

    :param result_dir: dictionary with paths to all household database files
    """
    houses_dir = result_dir / "Houses"
    house_dbs = {}
    # the Houses directory contains one subdirectory per house
    for house_dir in houses_dir.iterdir():
        assert house_dir.is_dir(), f"Unexpected file found: {house_dir}"
        # import each household database file from the house
        for db_file in house_dir.glob("Results.HH*"):
            assert db_file.is_dir() != (
                db_file.suffix == ".sqlite"
            ), "Invalid database format"
            hh_name = db_file.name.removeprefix("Results.").removesuffix(".sqlite")
            hh_id = f"{house_dir.name}_{hh_name}"
            house_dbs[hh_id] = db_file
    logging.info(f"Collected {len(house_dbs)} household database files")
    return house_dbs
