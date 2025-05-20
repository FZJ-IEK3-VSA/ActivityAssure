"""Converts activity profiles from multiple LPG simulations to CSV files."""

import argparse
from pathlib import Path

import tqdm

from activityassure.preprocessing.lpg import activity_profiles


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Root directory of the raw input data",
        default="data/lpg_simulations/raw",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Root directory for the preprocessed result data",
        default="data/lpg_simulations/preprocessed",
        required=False,
    )
    args = parser.parse_args()
    input_dir = Path(args.input)
    result_dir = Path(args.output)
    assert input_dir.is_dir(), f"Invalid path: {input_dir}"

    # subdirectory where error messages from failed conversions are stored
    errors_dir = "errors"

    mapping_path = Path("examples/LoadProfileGenerator/activity_mapping_lpg.json")

    # expected directory structure: one directory per LPG template
    for template_dir in tqdm.tqdm(Path(input_dir).iterdir()):
        assert template_dir.is_dir(), f"Unexpected file found: {template_dir}"
        if template_dir.name == errors_dir:
            # skip the errors directory
            continue
        # each template directory contains one subdirectory per iteration
        for iteration_dir in template_dir.iterdir():
            assert iteration_dir.is_dir(), f"Unexpected file found: {iteration_dir}"
            # parse the template and calculation iteration from the directory
            id = iteration_dir.name
            template = iteration_dir.parent.name
            # determine the database filepath
            db_file = iteration_dir / "Results.HH1.sqlite"
            try:
                activity_profiles.convert_activity_profile_from_db_to_csv(
                    db_file, result_dir, mapping_path, id, template
                )
            except Exception as e:
                print(f"An error occurred while processing '{iteration_dir}': {e}")
                # if the LPG created a log file, move that to the errors directory
                logfile = iteration_dir / "Log.CommandlineCalculation.txt"
                if logfile.is_file():
                    logfile.rename(
                        input_dir
                        / errors_dir
                        / f"{template_dir.name}_{iteration_dir.name}_error.txt"
                    )
