"""
Generates the person characteristics for the LoadProfileGenerator
from the input database profilegenerator.db3.
"""

import json
from pathlib import Path
import sqlite3
from activityassure import profile_category
from activityassure.categorization_attributes import (
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
    "Living Pattern / Work From Home Part Time": WorkStatus.part_time,
}


def get_person_id(person: str, template: str) -> str:
    """
    Generates the person ID from the person name and template name
    from the LPG. The person name string from the LPG contains a
    template ID, but sometimes persons are reused in other templates,
    so the template ID has to be adjusted.

    :param person: person name string from LPG
    :param template: template name string from LPG
    :return: combined person ID
    """
    # format of person: "CHR01 Rubi""
    person_template, person_name = person.split(" ")
    # format of template: "CHR01 Couple both at Work"
    template_id = template.split(" ")[0]
    if person_template == template_id:
        return person
    print(f"Info: person '{person}' is used in template '{template_id}'")
    return f"{template_id} {person_name}"


def define_person_mapping(database_path: Path, result_path: Path):
    """
    Extracts person information from the LoadProfileGenerator database
    and creates a person characterstics file from that.

    :param database_path: path of the database file
    :param result_path: output path for the created characteristics file
    """
    assert database_path.is_file(), f"Input database of LPG is missing: {database_path}"
    # query the person information, including name, gender and the living pattern tag each
    # person has in his/her household
    con = sqlite3.connect(database_path)
    cur = con.cursor()
    query = """select tblPersons.Name, tblPersons.Age, tblHouseholdTemplates.Name, tblPersons.Gender1, tblLivingPatternTags.Name
from tblPersons inner join tblHHTemplatePerson on tblPersons.ID == tblHHTemplatePerson.PersonID
inner join tblLivingPatternTags on tblHHTemplatePerson.LivingPatternTagID == tblLivingPatternTags.ID
inner join tblHouseholdTemplates on tblHHTemplatePerson.HHTemplateID == tblHouseholdTemplates.ID
"""
    results = cur.execute(query)
    rows: list[tuple] = results.fetchall()

    # map all fields
    mapping = {
        get_person_id(person, template): profile_category.ProfileCategory(
            "DE", GENDER_MAPPING[gender], WORK_STATUS_MAPPING[tag]
        )
        for person, age, template, gender, tag in rows
    }

    # write all characteristics to a json file
    dict_mapping = {n: p.to_dict() for n, p in sorted(mapping.items())}  # type: ignore
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w+", encoding="utf-8") as f:
        json.dump(dict_mapping, f, indent=4)
    print(f"Generated person characteristics file: {result_path}")


if __name__ == "__main__":
    lpg_main_db = Path("data/lpg_simulations/profilegenerator.db3")
    person_file = Path("examples/LoadProfileGenerator/data/person_characteristics.json")
    define_person_mapping(lpg_main_db, person_file)
