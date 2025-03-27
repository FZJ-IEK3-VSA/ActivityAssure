from datetime import timedelta
from pathlib import Path
from activityassure import activity_mapping
from activityassure.activity_profile import SparseActivityProfile
from activityassure.input_data_processing import load_model_data
from activityassure.plausibility_checks.profile_report import (
    ProfileReport,
)
from activityassure.plausibility_checks import sleep_checks


def check_activity_profile(profile: SparseActivityProfile):
    report = ProfileReport()
    print(f"Checking profile {profile.filename} ({profile.duration()})")
    sleep_checks.check_sleep_each_night(profile, report)
    print(report.get_str_report())


def check_activity_profiles(full_year_profiles):
    for profile in full_year_profiles:
        check_activity_profile(profile)


def main():
    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)
    # input data paths
    lpg_input_dir = Path("examples/LoadProfileGenerator/data")
    input_path = lpg_input_dir / "preprocessed"
    mapping_file = lpg_input_dir / "activity_mapping.json"
    person_trait_file = lpg_input_dir / "person_characteristics.json"

    # load and preprocess all input data
    full_year_profiles = load_model_data.load_activity_profiles_from_csv(
        input_path, person_trait_file, profile_resolution, False
    )

    mapping, activities = activity_mapping.load_mapping_and_activities(mapping_file)
    for full_year_profile in full_year_profiles:
        full_year_profile.apply_activity_mapping(mapping)

    check_activity_profiles(full_year_profiles)


if __name__ == "__main__":
    main()
