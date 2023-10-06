import json
import os
from activity_profile_validator.hetus_data_processing.attributes.person_attributes import Categories, WorkStatus
from activity_profile_validator.hetus_data_processing.hetus_values import Sex

# the available person categories and characteristics are assumed to be fixed as follows:
# available_characteristics = {
#     "sex": ["male", "female"],
#     "work status": ["full_time", "part_time", "unemployed", "retired", "student"]
# }

def save_person_mapping(directory: str):
    #TODO: (automatically?) create complete mapping for all persons/households
    mapping = {
        "CHR01 Rubi (23/Female)": {
            "Sex": Sex.female,
            Categories.work_status: WorkStatus.full_time
        },
        "CHR01 Sami (25/Male)": {
            "Sex": Sex.male,
            Categories.work_status: WorkStatus.full_time
        }
    }

    path = os.path.join(directory, "person_traits.json")
    with open(path, "w+", encoding="utf-8") as f:
        json.dump(mapping, f)



if __name__ == "__main__":
    directory = ".\\data\\lpg"
    save_person_mapping(directory)