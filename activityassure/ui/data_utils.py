"""
Helper functions for handling data, paths and labels for the web app.
"""

import glob
from pathlib import Path
import pandas as pd
from plotly.graph_objects import Figure  # type: ignore

from activity_validator import activity_mapping
from activity_validator.ui import datapaths
from activity_validator.profile_category import ProfileCategory
from activity_validator.validation_statistics import ValidationSet


def ptype_to_label(profile_type: ProfileCategory) -> str:
    return " - ".join(profile_type.to_list())


def ptype_from_label(profile_type_str: str) -> ProfileCategory:
    return ProfileCategory.from_iterable(profile_type_str.split(" - "))


def get_files(path: Path) -> list[Path]:
    assert path.exists(), f"Invalid path: {path}"
    return [f for f in path.iterdir() if f.is_file()]


def get_profile_type_paths(path: Path) -> dict[ProfileCategory, Path]:
    input_prob_files = get_files(path)
    profile_types = {ProfileCategory.from_filename(p): p for p in input_prob_files}
    if None in profile_types:
        raise RuntimeError("Invalid file name: could not parse profile type")
    return profile_types  # type: ignore


def get_profile_type_labels(path: Path) -> list[str]:
    profile_types = get_profile_type_paths(path)
    return [ptype_to_label(p) for p in profile_types.keys()]


def get_file_path(
    directory: Path, profile_type: ProfileCategory, ext: str = "*"
) -> Path | None:
    """
    Searches for the statistics file belonging to a specific ProfileCategory
    in a certain subdirectory.

    :param directory: the subdirectory to search in
    :param profile_type: the ProfileCategory for which to look up the path
    :param ext: file extension, defaults to "*"
    :raises RuntimeError: if the file could not be identified unambiguously
    :return: the path of the matching file, or None if no file was found
    """
    filter = directory / ("*" + profile_type.construct_filename() + f".{ext}")

    # find the correct file
    files = glob.glob(str(filter))
    if len(files) == 0:
        # no file for this profile type exists in this directory
        return None
    if len(files) > 1:
        raise RuntimeError(f"Found multiple files for the same profile type: {files}")
    return Path(files[0])


def get_final_activity_order(
    path_val: Path,
    path_input: Path,
    default_order: list[str] = [],
):
    """
    Returns the final activity order to use for all plots with multiple activities.

    :param path_val: base path to the validation data
    :param path_input: base path to the input data
    :param default_order: a default activity ordering to apply, defaults to []
    :return: ordered list of all actually occurring activities
    """
    act_val = ValidationSet.load_activities(path_val)
    act_input = ValidationSet.load_activities(path_input)
    combined = activity_mapping.check_activity_lists(act_input, act_val)
    if not default_order:
        return combined
    # add all activities in default order if they actually occur
    ordered = [a for a in default_order if a in combined]
    # append all additional activities missing in default order
    ordered += [a for a in combined if a not in ordered]
    return ordered


def reorder_activities(data: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    """
    Orders the columns of the dataframe according to the passed list.

    :param data: data to order
    :param order: order to apply to the columns
    :return: ordered data
    """
    ordered_cols = [a for a in order if a in data.columns]
    return data[ordered_cols]


def save_plot(
    figure: Figure,
    subdir: str,
    name: str,
    profile_type: ProfileCategory | None = None,
    base_path: str | Path = datapaths.output_path,
    svg: bool = True,
) -> Figure:
    if not isinstance(base_path, Path):
        base_path = Path(base_path)
    # build the full result path
    path = base_path / subdir
    # use another
    if profile_type is not None:
        ptypedir = profile_type.construct_filename("")
        path /= ptypedir.removeprefix("_")
    # make sure the directory exists
    path.mkdir(parents=True, exist_ok=True)
    name = name.replace("/", "_")
    name += ".svg" if svg else ".png"
    filepath = path / name
    figure.write_image(filepath)
    return figure
