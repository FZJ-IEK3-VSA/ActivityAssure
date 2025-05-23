"""
Example that demonstrates usage of ETHOS.ActivityAssure by validating
the city simulation of the LoadProfileGenerator.
"""

from datetime import timedelta
import logging
from pathlib import Path

from activityassure import validation
from activityassure.input_data_processing import process_model_data


def calc_citysim_statistics_and_validate(
    preprocessed_data_path: Path, city_stats_path: Path
):
    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)

    # additional files with mappings and person information
    lpg_example_data_dir = Path("examples/LoadProfileGenerator/data")
    merging_file = lpg_example_data_dir / "activity_merging.json"
    mapping_file = lpg_example_data_dir / "activity_mapping.json"
    person_trait_file = lpg_example_data_dir / "person_characteristics.json"
    # validation statistics paths
    validation_stats_path = Path(
        "data/validation_data_sets/activity_validation_data_set"
    )
    validation_stats_path_merged = Path(f"{validation_stats_path}_merged")
    # input statistics path
    # here the statistics of the input data and the validation results will be stored

    # the LoadProfileGenerator simulates cooking and eating as one activity, therefore these
    # two activities must be merged in the validation statistics
    process_model_data.merge_activities(
        validation_stats_path, merging_file, validation_stats_path_merged
    )

    # calculate statistics for the input model data
    input_statistics = process_model_data.process_model_data(
        preprocessed_data_path,
        mapping_file,
        person_trait_file,
        profile_resolution,
        categories_per_person=False,
    )
    # save the created statistics
    input_statistics.save(city_stats_path)

    # apply the activity merging to the city simulation results as well
    city_stats_path_merged = Path(f"{city_stats_path}_merged")
    process_model_data.merge_activities(
        city_stats_path, merging_file, city_stats_path_merged
    )

    # validate the input data using the statistics
    validation.default_validation(city_stats_path_merged, validation_stats_path_merged)

    # additionally, aggregate both statistics to national level and validate with that
    validation_national = Path(f"{validation_stats_path_merged}_national")
    process_model_data.aggregate_to_national_level(
        validation_stats_path_merged, validation_national
    )
    citysim_national = Path(f"{city_stats_path_merged}_national")
    process_model_data.aggregate_to_national_level(
        city_stats_path_merged, citysim_national
    )

    validation.default_validation(citysim_national, validation_national)


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # path to a directory with preprocessed activitiy profiles in csv format
    
    postproc_path = Path("C:/LPG/Results/scenario_julich-grosse-rurstr/Postprocessed")
    profiles_dir = postproc_path / "activity_profiles"
    statistics_path = postproc_path / "activityassure_statistics"

    calc_citysim_statistics_and_validate(profiles_dir, statistics_path)


if __name__ == "__main__":
    main()
