from pathlib import Path
from dash import Dash, Output, Input, State, html, dcc, callback, MATCH  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import plotly.express as px  # type: ignore
import uuid

from activity_validator.hetus_data_processing import activity_profile
from activity_validator.ui import data_utils, datapaths, plots


class MainValidationView(html.Div):
    """
    A reusable component containing a profile category selector
    and a graph showing the corresponding activity probability
    curves.
    """

    class ids:
        # A set of functions that create pattern-matching callbacks of the subcomponents
        dropdown = lambda aio_id: {
            "component": "MainValidationView",
            "subcomponent": "dropdown",
            "aio_id": aio_id,
        }
        validation_graph = lambda aio_id: {
            "component": "MainValidationView",
            "subcomponent": "validation probability graph",
            "aio_id": aio_id,
        }
        input_graph = lambda aio_id: {
            "component": "MainValidationView",
            "subcomponent": "input probability graph",
            "aio_id": aio_id,
        }
        difference_graph = lambda aio_id: {
            "component": "MainValidationView",
            "subcomponent": "probability difference graph",
            "aio_id": aio_id,
        }
        kpi_view = lambda aio_id: {
            "component": "MainValidationView",
            "subcomponent": "kpi view",
            "aio_id": aio_id,
        }
        per_activity_graphs = lambda aio_id: {
            "component": "MainValidationView",
            "subcomponent": "graphs per activity",
            "aio_id": aio_id,
        }

    # Define the arguments of the component
    def __init__(
        self,
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
        validation_types = data_utils.get_profile_type_labels(
            datapaths.validation_path / datapaths.prob_dir
        )
        input_types = data_utils.get_profile_type_labels(
            datapaths.input_data_path / datapaths.prob_dir
        )
        all_types = sorted(list(set(validation_types) | set(input_types)))

        # Define the component's layout
        super().__init__(
            dbc.Card(
                dbc.CardBody(
                    [
                        # dcc.Store(data=str(validation_path), id=self.ids.store(aio_id)),
                        dcc.Dropdown(
                            all_types,
                            input_types[0],
                            id=self.ids.dropdown(aio_id),
                            className="mb-3",
                            **dropdown_props,
                        ),
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.H2(
                                                "Validation Data",
                                                style={"textAlign": "center"},
                                            ),
                                            html.Div(
                                                id=self.ids.validation_graph(aio_id)
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.H2(
                                                "LoadProfileGenerator Data",
                                                style={"textAlign": "center"},
                                            ),
                                            html.Div(id=self.ids.input_graph(aio_id)),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.H2(
                                                "Difference",
                                                style={"textAlign": "center"},
                                            ),
                                            html.Div(
                                                id=self.ids.difference_graph(aio_id)
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                            className="mb-3",
                        ),
                        html.Div(id=self.ids.kpi_view(aio_id), className="mb-3"),
                        html.Div(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            html.H2(
                                                "Activity Frequencies per Day",
                                                style={"textAlign": "center"},
                                            )
                                        ),
                                        dbc.Col(
                                            html.H2(
                                                "Activity Durations",
                                                style={"textAlign": "center"},
                                            )
                                        ),
                                        dbc.Col(
                                            html.H2(
                                                "Activity Probabilities",
                                                style={"textAlign": "center"},
                                            )
                                        ),
                                        dbc.Col(
                                            html.H2(
                                                "Comparison Metrics",
                                                style={"textAlign": "center"},
                                            )
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                html.Div(id=self.ids.per_activity_graphs(aio_id)),
                            ]
                        ),
                    ],
                )
            )
        )

    @callback(
        Output(ids.validation_graph(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_validation_graph(profile_type_str):
        return plots.update_prob_curves(
            profile_type_str, datapaths.validation_path / datapaths.prob_dir
        )

    @callback(
        Output(ids.input_graph(MATCH), "children"), Input(ids.dropdown(MATCH), "value")
    )
    def update_input_graph(profile_type_str):
        return plots.update_prob_curves(
            profile_type_str, datapaths.input_data_path / datapaths.prob_dir
        )

    @callback(
        Output(ids.difference_graph(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_diff_graph(profile_type_str):
        return plots.update_prob_curves(
            profile_type_str, datapaths.input_data_path / datapaths.diff_dir, area=False
        )

    @callback(
        Output(ids.kpi_view(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_overall_kpis(profile_type_str):
        return [plots.titled_card(None, "TBD")]

    @callback(
        Output(ids.per_activity_graphs(MATCH), "children"),
        Input(ids.dropdown(MATCH), "value"),
    )
    def update_graphs_per_activity_type(profile_type_str):
        profile_type = data_utils.ptype_from_label(profile_type_str)
        freq = plots.histogram_per_activity(profile_type, datapaths.freq_dir)
        dur = plots.histogram_per_activity(profile_type, datapaths.duration_dir, True)
        prob = plots.prob_curve_per_activity(profile_type, datapaths.prob_dir)
        kpis = plots.kpi_table(profile_type, datapaths.metrics_dir)
        if not freq:
            # no data available for this profile type
            return plots.titled_card(plots.replacement_text())
        assert (
            freq.keys() == dur.keys() == prob.keys()
        ), "Missing data for some activity types"
        # build rows, one for each activity
        rows = [
            dbc.Row(
                [
                    dbc.Col(plots.titled_card(x, a.title()))
                    for x in (freq[a], dur[a], prob[a], kpis[a])
                ],
                className="mb-3",
            )
            for a in freq.keys()
        ]
        return rows
