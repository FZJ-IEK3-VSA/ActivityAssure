import json
import os
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.attributes.person_attributes import (
    Sex,
    WorkStatus,
)


def define_person_mapping(path: str):
    # TODO: (automatically?) create complete mapping for all persons/households
    mapping = {
        "CHR01 Rubi (23/Female)": activity_profile.ProfileType(
            "DE", Sex.female, WorkStatus.full_time
        ),
        "CHR01 Sami (25/Male)": activity_profile.ProfileType(
            "DE", Sex.male, WorkStatus.full_time
        ),
    }
    dict_mapping = {n: p.to_dict() for n, p in mapping.items()}  # type: ignore

    path = os.path.join(path)
    with open(path, "w+", encoding="utf-8") as f:
        json.dump(dict_mapping, f, indent=4)


if __name__ == "__main__":
    path = ".\\data\\lpg\\person_types.json"
    define_person_mapping(path)
