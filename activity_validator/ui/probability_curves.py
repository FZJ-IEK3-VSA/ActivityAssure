from datetime import datetime, timedelta
from pathlib import Path
from dash import Dash, Output, Input, State, html, dcc, callback, MATCH
import plotly.express as px
import uuid

import pandas as pd
from activity_validator.hetus_data_processing import activity_profile

from activity_validator.hetus_data_processing.activity_profile import ProfileType


def get_files(path: Path) -> list[Path]:
    assert path.exists(), f"Invalid path: {path}"
    return [f for f in path.iterdir() if f.is_file()]


def get_profile_types(path: Path) -> list[ProfileType]:
    input_prob_files = get_files(path)
    profile_types = [ProfileType.from_filename(p)[1] for p in input_prob_files]
    if None in profile_types:
        raise RuntimeError("Invalid file name: could not parse profile type")
    return profile_types  # type: ignore


# All-in-One Components should be suffixed with 'AIO'
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
        profile_types = get_profile_types(path)
        assert None not in profile_types, "Invalid filename"
        profile_type_strs = [" - ".join(pt.to_tuple()) for pt in profile_types]

        # Define the component's layout
        super().__init__(
            [  # Equivalent to `html.Div([...])`
                dcc.Store(data=str(path), id=self.ids.store(aio_id)),
                dcc.Dropdown(
                    profile_type_strs,
                    profile_type_strs[0],
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
        # load the appropriate file depending on the profile type
        profile_type = ProfileType.from_iterable(value.split(" - "))
        filename = profile_type.construct_filename("prob") + ".csv"
        _, data = activity_profile.load_df(Path(path) / filename)

        data = data.T

        # generate 24h time range starting at 04:00
        resolution = timedelta(days=1) / len(data)
        start_time = datetime.strptime("04:00", "%H:%M")
        end_time = start_time + timedelta(days=1) - resolution
        time_values = pd.date_range(start_time, end_time, freq=resolution)

        # plot the data
        fig = px.area(
            data,
            x=time_values,
            y=data.columns,
        )
        return fig
