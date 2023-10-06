import json
import os
from activity_validator.hetus_data_processing.attributes.person_attributes import Categories, WorkStatus
from activity_validator.hetus_data_processing.hetus_values import Sex

# the available person categories and characteristics are assumed to be fixed as follows:
# available_characteristics = {
#     "sex": ["male", "female"],
#     "work status": ["full_time", "part_time", "unemployed", "retired", "student"]
# }

def save_person_mapping(path: str):
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

    path = os.path.join(path)
    with open(path, "w+", encoding="utf-8") as f:
        json.dump(mapping, f)



if __name__ == "__main__":
    path = ".\\data\\lpg\\person_traits.json"
    save_person_mapping(path)