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
from activity_validator.ui.file_utils import (
    get_file_path,
    get_profile_types,
    ptype_to_label,
)

from activity_validator.ui import file_utils


def create_profile_type_selector(
    profile_types: Iterable[ProfileType], dropdown_props=None
):
    profile_type_strs = [ptype_to_label(pt) for pt in profile_types]
    return dcc.Dropdown(
        profile_type_strs,
        profile_type_strs[0],
        **dropdown_props,
    )


class AIOSelectableProbabilityCurves(html.Div):
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
        graph = lambda aio_id: {
            "component": "AIOSelectableProbabilityCurves",
            "subcomponent": "graph",
            "aio_id": aio_id,
        }

    # Define the arguments of the component
    def __init__(self, path: Path, dropdown_props=None, graph_props=None, aio_id=None):
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
        profile_type_labels = file_utils.get_profile_type_labels(path)

        # Define the component's layout
        super().__init__(
            [  # Equivalent to `html.Div([...])`
                dcc.Store(data=str(path), id=self.ids.store(aio_id)),
                dcc.Dropdown(
                    profile_type_labels,
                    profile_type_labels[0],
                    id=self.ids.dropdown(aio_id),
                    **dropdown_props,
                ),
                dcc.Graph(id=self.ids.graph(aio_id), **graph_props),
            ],
        )

    # Define this component's stateless pattern-matching callback
    # that will apply to every instance of this component.
    @callback(
        Output(ids.graph(MATCH), "figure"),
        Input(ids.dropdown(MATCH), "value"),
        State(ids.store(MATCH), "data"),
    )
    def update_graph(value, path):
        # get the appropriate file suffix depending on the profile type
        profile_type = ProfileType.from_iterable(value.split(" - "))
        filepath = get_file_path(Path(path), profile_type)
        # load the correct file
        _, data = activity_profile.load_df(filepath)

        data = data.T

        # generate 24h time range starting at 04:00
        resolution = timedelta(days=1) / len(data)
        start_time = datetime.strptime("04:00", "%H:%M")
        end_time = start_time + timedelta(days=1) - resolution
        time_values = pd.date_range(start_time, end_time, freq=resolution)

        # TODO: quick and dirty - make nicer solution
        plotting_func = px.area if "diff" not in str(filepath) else px.line

        # plot the data
        fig = plotting_func(
            data,
            x=time_values,
            y=data.columns,
        )
        return fig
