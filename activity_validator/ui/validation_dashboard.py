from datetime import datetime, timedelta
from pathlib import Path
from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile

from activity_validator.hetus_data_processing.activity_profile import ProfileType

df = pd.read_csv(
    "https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv"
)

app = Dash(__name__)

validation_path = Path("data/validation")
input_data_path = Path("data/lpg/results")

prob_path = "probability_profiles"


def get_files(path: Path) -> list[Path]:
    assert path.exists(), f"Invalid path: {path}"
    return [f for f in path.iterdir() if f.is_file()]


input_prob_files = get_files(validation_path / prob_path)
profile_types = [ProfileType.from_filename(p)[1] for p in input_prob_files]
assert None not in profile_types, "Invalid filename"
profile_type_strs = [" - ".join(pt.to_tuple()) for pt in profile_types]


app.layout = html.Div(
    [
        html.H1(children="Activity Profile Validator", style={"textAlign": "center"}),
        dcc.Dropdown(profile_type_strs, profile_type_strs[0], id="profile-type"),
        dcc.Graph(id="probability-curve"),
    ]
)


@callback(Output("probability-curve", "figure"), Input("profile-type", "value"))
def update_graph(value):
    profile_type = ProfileType.from_iterable(value.split(" - "))
    # path = ProfileType.from_iterable(profile_type)
    base_path = validation_path / prob_path
    filename = profile_type.construct_filename("prob") + ".csv"
    _, data = activity_profile.load_df(base_path / filename)
    data = data.T

    resolution = timedelta(days=1) / len(data)
    start_time = datetime.strptime("04:00", "%H:%M")
    end_time = start_time + timedelta(days=1) - resolution
    time_values = pd.date_range(start_time, end_time, freq=resolution)

    fig = px.area(
        data,
        x=time_values,
        y=data.columns,
    )
    return fig


if __name__ == "__main__":
    app.run(debug=True)
