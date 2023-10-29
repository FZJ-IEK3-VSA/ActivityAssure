from datetime import datetime, timedelta
import glob
from pathlib import Path
from typing import Iterable
from dash import Dash, Output, Input, State, html, dcc, callback, MATCH
import plotly.express as px
import uuid

import pandas as pd
from activity_validator.hetus_data_processing import activity_profile

from activity_validator.hetus_data_processing.activity_profile import ProfileType

from activity_validator.ui import file_utils

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


def get_date_range(num_values: int):
    # generate 24h time range starting at 04:00
    resolution = timedelta(days=1) / num_values
    start_time = datetime.strptime("04:00", "%H:%M")
    end_time = start_time + timedelta(days=1) - resolution
    time_values = pd.date_range(start_time, end_time, freq=resolution)
    return time_values


def stacked_prob_curves(filepath: Path | None, area: bool = True):
    if filepath is None or not filepath.is_file():
        return html.Div(children=["No data available"], style={"textAlign": "center"})
    # load the correct file
    _, data = activity_profile.load_df(filepath)
    # transpose data for plotting
    data = data.T
    time_values = get_date_range(len(data))
    # select plot type
    plotting_func = px.area if area else px.line
    # plot the data
    fig = plotting_func(
        data,
        x=time_values,
        y=data.columns,
    )
    return dcc.Graph(figure=fig)


def update_prob_curves(profile_type_str: str, directory: Path):
    # get the appropriate file suffix depending on the profile type
    profile_type = file_utils.ptype_from_label(profile_type_str)
    filepath = file_utils.get_file_path(directory, profile_type)
    result = stacked_prob_curves(filepath)
    return result


def draw_activity_figure(subdir: str, profile_type: ProfileType):
    # profile_type = ProfileType.from_iterable(value.split(" - "))
    dv = file_utils.load_data_by_type(validation_path / subdir, profile_type)
    di = file_utils.load_data_by_type(input_data_path / subdir, profile_type)
    di.rename(columns={c: c + " - LPG" for c in di.columns}, inplace=True)

    data_sets = []
    for col in dv.columns:
        c2 = col + " - LPG"
        if not c2 in di.columns:
            continue
        d = pd.concat([dv[col], di[c2]], axis=1)
        data_sets.append(d)
    return [dcc.Graph(figure=px.ecdf(d)) for d in data_sets]


class MainValidationView(html.Div):
    """
    A reusable component containing a profile category selector
    and a graph showing the corresponding activity probability
    curves.
    """

    class ids:
        # A set of functions that create pattern-matching callbacks of the subcomponents
        store = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "store",
            "aio_id": aio_id,
        }
        dropdown = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "dropdown",
            "aio_id": aio_id,
        }
        validation_graph = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "validation probability graph",
            "aio_id": aio_id,
        }
        input_graph = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "input probability graph",
            "aio_id": aio_id,
        }

    # Define the arguments of the component
    def __init__(
        self,
        validation_path: Path,
        input_data_path: Path,
        dropdown_props=None,
        graph_props=None,
        aio_id=None,
    ):
        """
        - `aio_id` - The All-in-One component ID used to generate the markdown and dropdown components's dictionary IDs.

        The All-in-One component dictionary IDs are available as
        - MarkdownWithColorAIO.ids.dropdown(aio_id)
        - MarkdownWithColorAIO.ids.markdown(aio_id)
        """
        dropdown_props = dropdown_props or {}
        graph_props = graph_props or {}

        if not aio_id:
            # if not set by user, define a random ID
            aio_id = str(uuid.uuid4())

        # get available profile categories
        validation_types = file_utils.get_profile_type_labels(
            validation_path / prob_dir
        )
        input_types = file_utils.get_profile_type_labels(input_data_path / prob_dir)
        all_types = list(set(validation_types) | set(input_types))

        # get filepaths

        # Define the component's layout
        super().__init__(
            [
                dcc.Store(data=str(validation_path), id=self.ids.store(aio_id)),
                dcc.Dropdown(
                    all_types,
                    all_types[0],
                    id=self.ids.dropdown(aio_id),
                    **dropdown_props,
                ),
                html.Div(
                    [
                        html.H2("Validation Data", style={"textAlign": "center"}),
                        html.Div(id=self.ids.validation_graph(aio_id)),
                    ]
                ),
                html.Div(
                    [
                        html.H2(
                            "LoadProfileGenerator Data", style={"textAlign": "center"}
                        ),
                        html.Div(id=self.ids.input_graph(aio_id)),
                    ]
                ),
                html.Div(
                    [
                        html.H2("Difference", style={"textAlign": "center"}),
                        # MainValidationView(input_data_path / comp_dir / diff_dir),
                        dcc.Graph(),
                    ]
                ),
                # html.Div(
                #     [
                #         html.H2("Activity Frequencies", style={"textAlign": "center"}),
                #         html.Div(draw_activity_figure(freq_dir, test_profile_type)),
                #     ]
                # ),
            ],
        )

    @callback(
        Output(ids.validation_graph(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_validation_graph(profile_type_str):
        return [update_prob_curves(profile_type_str, validation_path / prob_dir)]

    @callback(
        Output(ids.input_graph(MATCH), "children"), Input(ids.dropdown(MATCH), "value")
    )
    def update_input_graph(profile_type_str):
        return [update_prob_curves(profile_type_str, input_data_path / prob_dir)]
