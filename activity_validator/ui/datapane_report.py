from datetime import datetime, timedelta
import glob
from pathlib import Path
import datapane as dp  # type: ignore
import pandas as pd
import plotly.express as px  # type: ignore

from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.ui.data_utils import get_files


# default data paths
validation_path = Path("data/validation_data")
# validation_path = Path("data/validation_data EU")
input_data_path = Path("data/lpg/results")
# data subdirectories
prob_dir = "probability_profiles"
freq_dir = "activity_frequencies"
duration_dir = "activity_durations"
comp_dir = "comparison"
metrics_dir = "metrics"
diff_dir = "differences"


def get_file_path(directory: Path, profile_type: ProfileType, ext: str = "*") -> Path:
    filter = directory / ("*" + profile_type.construct_filename() + f".{ext}")

    # find the correct file
    files = glob.glob(str(filter))
    if len(files) == 0:
        raise RuntimeError(f"Could not find a matching file: {filter}")
    if len(files) > 1:
        raise RuntimeError(f"Found multiple files for the same profile type: {files}")
    return Path(files[0])


def ptype_to_label(profile_type: ProfileType) -> str:
    return " - ".join(profile_type.to_tuple())


def get_profile_types(path: Path) -> dict[ProfileType, Path]:
    input_prob_files = get_files(path)
    profile_types = {ProfileType.from_filename(p)[1]: p for p in input_prob_files}
    if None in profile_types:
        raise RuntimeError("Invalid file name: could not parse profile type")
    return profile_types  # type: ignore


def draw_prob_curves(profile_type: ProfileType, filepath: Path):
    if filepath is None or not filepath.is_file():
        return dp.Text("Data not available")

    _, data = activity_profile.load_df(filepath)

    data = data.T

    # generate 24h time range starting at 04:00
    resolution = timedelta(days=1) / len(data)
    start_time = datetime.strptime("04:00", "%H:%M")
    end_time = start_time + timedelta(days=1) - resolution
    time_values = pd.date_range(start_time, end_time, freq=resolution)

    label = ptype_to_label(profile_type)
    # plot the data
    fig = px.area(
        data,
        x=time_values,
        y=data.columns,
    )
    return dp.Plot(fig, label=label)


def comparison_prob_curves(profile_type: ProfileType, file_valid: Path, file_in: Path):
    return dp.Group(
        draw_prob_curves(profile_type, file_valid),
        draw_prob_curves(profile_type, file_in),
        label=ptype_to_label(profile_type),
    )


def create_validation_tab():
    files_val = get_profile_types(validation_path / prob_dir)
    files_in = get_profile_types(input_data_path / prob_dir)
    files_joint = {p: (f, files_in.get(p, None)) for p, f in files_val.items()}

    prob_curves_valid = [
        comparison_prob_curves(p, f1, f2) for p, (f1, f2) in files_joint.items()
    ]

    return dp.Page(
        title="Validation",
        blocks=[dp.Select(blocks=prob_curves_valid, type=dp.SelectType.DROPDOWN)],
    )


def country_overview_tab():
    return dp.Page(title="Country Overview", blocks=[dp.Text("TBD")])


def cross_country_tab():
    return dp.Page(title="Cross-country Comparison", blocks=[dp.Text("TBD")])


def create_report():
    return dp.Blocks(
        create_validation_tab(), country_overview_tab(), cross_country_tab()
    )


if __name__ == "__main__":
    report = create_report()
    path = Path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    dp.save_report(report, path / "activity_validator.html", open=True)
