"""
Generates the person characteristics and the basic activity mapping for the 
LoadProfileGenerator from the input database profilegenerator.db3.
"""

import json
from pathlib import Path
import sqlite3
from activity_validator import profile_category
from activity_validator.categorization_attributes import (
    Sex,
    WorkStatus,
)

# Define mappings for the LPG database fields
GENDER_MAPPING = {0: Sex.male, 1: Sex.female}
WORK_STATUS_MAPPING = {
    # "Living Pattern / All": None,  # no person has this tag
    "Living Pattern / Kindergarden": WorkStatus.student,
    "Living Pattern / Maid / Day Maid": WorkStatus.full_time,
    "Living Pattern / Office Job": WorkStatus.full_time,
    "Living Pattern / Office Job / Early (5-7am)": WorkStatus.full_time,
    "Living Pattern / Office Job / Late (9-11am)": WorkStatus.full_time,
    "Living Pattern / Office Job / Medium (7-9am)": WorkStatus.full_time,
    "Living Pattern / Office Worker": WorkStatus.full_time,
    "Living Pattern / Part Time Job": WorkStatus.part_time,
    "Living Pattern / Retiree": WorkStatus.retired,
    "Living Pattern / School": WorkStatus.student,
    "Living Pattern / School / Medium (7-9am)": WorkStatus.student,
    "Living Pattern / Shift work": WorkStatus.full_time,
    "Living Pattern / Shift work / 3 Shifts A": WorkStatus.full_time,
    "Living Pattern / Shift work / 3 Shifts B": WorkStatus.full_time,
    "Living Pattern / Stay at Home": WorkStatus.unemployed,
    "Living Pattern / Stay at Home / Drifting": WorkStatus.unemployed,
    "Living Pattern / Stay at Home / Regular": WorkStatus.unemployed,
    "Living Pattern / Two Shift Work": WorkStatus.full_time,
    "Living Pattern / University": WorkStatus.student,
    "Living Pattern / University / Student Independent": WorkStatus.student,
    "Living Pattern / University / Student Living at Home": WorkStatus.student,
    "Living Pattern / Work From Home": WorkStatus.full_time,
    "Living Pattern / Work From Home / Full Time 5 days": WorkStatus.full_time,
    "Living Pattern / Work From Home / Part Time": WorkStatus.part_time,
}


def person_name(full_name: str) -> str:
    """
    Extracts the actual person name out of the
    full name string, e.g.: 'CHR01 Rubi' -> 'Rubi'

    :param full_name: the full name incl. household id
    :return: the short name
    """
    return full_name.split(" ")[1]


def define_person_mapping(database_path: Path, result_path: Path):
    assert database_path.is_file(), f"Input database of LPG is missing: {database_path}"
    # query the person information, including name, gender and the living pattern tag each
    # person has in his/her household
    con = sqlite3.connect(database_path)
    cur = con.cursor()
    query = """select tblPersons.Name, tblPersons.Gender1, tblLivingPatternTags.Name
from tblPersons inner join tblCHHPersons on tblPersons.ID == tblCHHPersons.PersonID inner join tblLivingPatternTags on tblCHHPersons.LivingPatternTagID == tblLivingPatternTags.ID"""
    results = cur.execute(query)
    rows: list[tuple] = results.fetchall()

    # map all fields
    mapping = {
        person_name(person): profile_category.ProfileCategory(
            "DE", GENDER_MAPPING[gender], WORK_STATUS_MAPPING[tag]
        )
        for person, gender, tag in rows
    }

    # write all characteristics to a json file
    dict_mapping = {n: p.to_title_dict() for n, p in mapping.items()}  # type: ignore
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w+", encoding="utf-8") as f:
        json.dump(dict_mapping, f, indent=4)
    print(f"Generated person characteristics file: {result_path}")


def generate_raw_activity_mapping(database_path: str, output_file):
    assert Path(
        database_path
    ).is_file(), f"Input database file of LPG is missing: {database_path}"
    con = sqlite3.connect(database_path)
    cur = con.cursor()
    query = "SELECT Name, AffCategory FROM tblAffordances"
    results = cur.execute(query)
    rows: list[tuple] = results.fetchall()

    # define preliminary mapping based on affordance category
    # categories mapped to None are ambiguous and need manual assignment
    category_mapping = {
        "Active Entertainment (Computer, Internet etc)": "pc",
        "Entertainment": None,
        "Office": "work",
        "Offline Entertainment": "other",
        "Outside recreation": "not at home",
        "Passive Entertainment (TV etc.)": None,
        "child care": "other",
        "cleaning": None,  # laundry is separate
        "cooking": "cook",
        "gardening and maintenance": "other",
        "hygiene": "personal care",
        "other": "other",
        "school": "education",
        "shopping": "not at home",
        "sleep": "sleep",
        "sports": None,
        "work": "work",
    }
    affordances = [(row[0], row[1]) for row in rows]
    mapping = {name: category_mapping[category] for name, category in affordances}
    # manually add vacation affordance
    mapping["taking a vacation"] = "not at home"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)
    print(f"Generated basic activity mapping file: {output_file}")


if __name__ == "__main__":
    lpg_main_db = Path("data/lpg/profilegenerator.db3")
    person_file = Path("data/lpg/person_characteristics.json")
    define_person_mapping(lpg_main_db, person_file)

    # output_file = "examples/activity_mapping_lpg.json"
    # generate_raw_activity_mapping(lpg_main_db, output_file)
