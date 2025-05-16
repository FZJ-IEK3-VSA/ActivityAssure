"""
Example that demonstrates usage of ETHOS.ActivityAssure by validating
the LoadProfileGenerator.
"""

from datetime import timedelta
import logging
from pathlib import Path

from activityassure.input_data_processing import process_model_data
from activityassure import validation


if __name__ == "__main__":
    country = "DE"
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)
    # input data paths
    lpg_input_dir = Path("examples/LoadProfileGenerator/data")
    input_data_path = lpg_input_dir / "preprocessed"
    merging_file = lpg_input_dir / "activity_merging.json"
    mapping_file = lpg_input_dir / "activity_mapping.json"
    person_trait_file = lpg_input_dir / f"person_characteristics_{country}.json"
    # validation statistics paths
    validation_stats_path = Path(
        "data/validation_data_sets/activity_validation_data_set"
    )
    validation_stats_path_merged = Path(f"{validation_stats_path}_merged")
    # input statistics path
    # here the statistics of the input data and the validation results will be stored
    input_stats_path = Path(f"data/validation/lpg_example/{country}")

    # the LoadProfileGenerator simulates cooking and eating as one activity, therefore these
    # two activities must be merged in the validation statistics
    process_model_data.merge_activities(
        validation_stats_path, merging_file, validation_stats_path_merged
    )

    # calculate statistics for the input model data
    input_statistics = process_model_data.process_model_data(
        input_data_path,
        mapping_file,
        person_trait_file,
        profile_resolution,
        categories_per_person=False,
    )
    # save the created statistics
    input_statistics.save(input_stats_path)

    # validate the input data using the statistics
    validation.default_validation(input_stats_path, validation_stats_path_merged)
