from dash import Output, Input, State, html, dcc, callback, no_update, MATCH  # type: ignore
import dash_bootstrap_components as dbc  # type: ignore
import uuid

from activityassure.ui.config import config
from activityassure import comparison_indicators
from activityassure.ui import data_utils, datapaths, plots


class MainValidationView(html.Div):
    """
    A reusable component containing a profile category selector
    and a graph showing the corresponding activity probability
    curves.
    """

    class ids:
        # A set of functions that create pattern-matching callbacks of the subcomponents
        def dropdown_valid(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "dropdown_validation",
                "aio_id": aio_id,
            }

        def dropdown_input(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "dropdown_input",
                "aio_id": aio_id,
            }

        def checklist_sync(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "checklist_sync",
                "aio_id": aio_id,
            }

        def validation_graph(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "validation probability graph",
                "aio_id": aio_id,
            }

        def input_graph(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "input probability graph",
                "aio_id": aio_id,
            }

        def difference_graph(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "probability difference graph",
                "aio_id": aio_id,
            }

        def kpi_view(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "kpi view",
                "aio_id": aio_id,
            }

        def per_activity_graphs(aio_id):
            return {
                "component": "MainValidationView",
                "subcomponent": "graphs per activity",
                "aio_id": aio_id,
            }

    synchronize_option = "Synchronize data types"

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
        common_types = sorted(list(set(validation_types) & set(input_types)))
        if not common_types:
            # no common categories - select the first category each
            initial_val = validation_types[0]
            initial_input = input_types[0]
            initial_sync = []
        else:
            # select the first common category
            initial_val = common_types[0]
            initial_input = common_types[0]
            initial_sync = [MainValidationView.synchronize_option]

        # Define the component's layout
        super().__init__(
            dbc.Card(
                dbc.CardBody(
                    [
                        # dcc.Store(data=str(validation_path), id=self.ids.store(aio_id)),
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Row(
                                                    [
                                                        html.H4(
                                                            "Validation Profile Category",
                                                            className="mb-3",
                                                        ),
                                                        html.H4(
                                                            config.model_name
                                                            + " Profile Category",
                                                            className="mb-3",
                                                        ),
                                                    ]
                                                ),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                dbc.Row(
                                                    [
                                                        dcc.Dropdown(
                                                            validation_types,
                                                            initial_val,
                                                            id=self.ids.dropdown_valid(
                                                                aio_id
                                                            ),
                                                            className="mb-3",
                                                            **dropdown_props,
                                                        ),
                                                        dcc.Dropdown(
                                                            all_types,
                                                            initial_input,
                                                            id=self.ids.dropdown_input(
                                                                aio_id
                                                            ),
                                                            className="mb-3",
                                                            **dropdown_props,
                                                        ),
                                                    ]
                                                ),
                                                width=3,
                                            ),
                                            dbc.Col(
                                                dcc.Checklist(
                                                    options=[
                                                        MainValidationView.synchronize_option
                                                    ],
                                                    value=initial_sync,
                                                    id=self.ids.checklist_sync(aio_id),
                                                )
                                            ),
                                        ],
                                    ),
                                ]
                            ),
                            className="mb-3",
                        ),
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div(
                                        children=[
                                            html.H2(
                                                "Validation Data",
                                                style={"textAlign": "center"},
                                            ),
                                            dcc.Loading(
                                                type="circle",
                                                id=self.ids.validation_graph(aio_id),
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        children=[
                                            html.H2(
                                                config.model_name + " Data",
                                                style={"textAlign": "center"},
                                            ),
                                            dcc.Loading(
                                                type="circle",
                                                id=self.ids.input_graph(aio_id),
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        children=[
                                            html.H2(
                                                "Difference",
                                                style={"textAlign": "center"},
                                            ),
                                            dcc.Loading(
                                                type="circle",
                                                id=self.ids.difference_graph(aio_id),
                                            ),
                                        ],
                                    ),
                                ]
                            ),
                            className="mb-3",
                        ),
                        dcc.Loading(
                            type="circle",
                            id=self.ids.kpi_view(aio_id),
                            className="mb-3",
                        ),
                        html.Br(),
                        html.Div(
                            children=[
                                html.Div(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.Card(
                                                        html.H2(
                                                            "Activity Frequencies per Day",
                                                            style={
                                                                "textAlign": "center"
                                                            },
                                                        )
                                                    )
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        html.H2(
                                                            "Activity Durations",
                                                            style={
                                                                "textAlign": "center"
                                                            },
                                                        )
                                                    )
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        html.H2(
                                                            "Activity Probabilities",
                                                            style={
                                                                "textAlign": "center"
                                                            },
                                                        )
                                                    )
                                                ),
                                                dbc.Col(
                                                    dbc.Card(
                                                        html.H2(
                                                            "Comparison Metrics",
                                                            style={
                                                                "textAlign": "center"
                                                            },
                                                        )
                                                    )
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dcc.Loading(
                                            type="circle",
                                            id=self.ids.per_activity_graphs(aio_id),
                                        ),
                                    ],
                                )
                            ],
                        ),
                    ],
                )
            )
        )

    @callback(
        Output(ids.dropdown_input(MATCH), "value"),
        Input(ids.dropdown_valid(MATCH), "value"),
        Input(ids.checklist_sync(MATCH), "value"),
        State(ids.dropdown_input(MATCH), "value"),
        prevent_initial_call=True,
    )
    def update_input_dropdown(
        profile_type_val: str, checklist: list[str] | None, profile_type_in: str
    ):
        if not checklist or MainValidationView.synchronize_option not in checklist:
            # the dropdowns behave independently
            return no_update
        # synchronize input dropdown to validation dropdown
        if profile_type_in == profile_type_val:
            # no update necessary
            return no_update
        return profile_type_val

    @callback(
        Output(ids.dropdown_input(MATCH), "disabled"),
        Input(ids.checklist_sync(MATCH), "value"),
    )
    def disable_input_dropdown(checklist: list[str] | None):
        return (
            checklist is not None and MainValidationView.synchronize_option in checklist
        )

    @callback(
        Output(ids.validation_graph(MATCH), "children"),
        Input(ids.dropdown_valid(MATCH), "value"),
    )
    def update_validation_graph(profile_type_str: str):
        return plots.update_stacked_prob_curves(
            profile_type_str, datapaths.validation_path / datapaths.prob_dir
        )

    @callback(
        Output(ids.input_graph(MATCH), "children"),
        Input(ids.dropdown_input(MATCH), "value"),
    )
    def update_input_graph(profile_type_str: str):
        return plots.update_stacked_prob_curves(
            profile_type_str, datapaths.input_data_path / datapaths.prob_dir
        )

    @callback(
        Output(ids.difference_graph(MATCH), "children"),
        Input(ids.dropdown_valid(MATCH), "value"),
        Input(ids.dropdown_input(MATCH), "value"),
    )
    def update_diff_graph(profile_type_valid: str, profile_type_input: str):
        profile_type_val = data_utils.ptype_from_label(profile_type_valid)
        filepath_val = data_utils.get_file_path(
            datapaths.validation_path / datapaths.prob_dir, profile_type_val
        )
        profile_type_in = data_utils.ptype_from_label(profile_type_input)
        filepath_in = data_utils.get_file_path(
            datapaths.input_data_path / datapaths.prob_dir, profile_type_in
        )
        figure = plots.stacked_diff_curve(filepath_val, filepath_in)
        if not figure:
            return plots.replacement_text()
        return [
            dcc.Graph(
                figure=data_utils.save_plot(
                    figure,
                    "probability profiles",
                    "difference",
                    profile_type=profile_type_in,
                )
            )
        ]

    @callback(
        Output(ids.kpi_view(MATCH), "children"),
        Input(ids.dropdown_valid(MATCH), "value"),
        Input(ids.dropdown_input(MATCH), "value"),
    )
    def update_overall_kpis(profile_type_valid: str, profile_type_input: str):
        ptype_val = data_utils.ptype_from_label(profile_type_valid)
        ptype_in = data_utils.ptype_from_label(profile_type_input)
        try:
            indicators, scaled, normed = plots.get_all_indicator_variants(
                ptype_val, ptype_in, True
            )
        except RuntimeError:
            return plots.titled_card(plots.replacement_text())
        table = plots.create_indicator_table(
            indicators,
            scaled,
            normed,
            comparison_indicators.ValidationIndicators.mean_column,
        )
        return [
            plots.titled_card(
                table, "Mean Indicator Values", style={"width": 600, "margin": "auto"}
            )
        ]

    @callback(
        Output(ids.per_activity_graphs(MATCH), "children"),
        Input(ids.dropdown_valid(MATCH), "value"),
        Input(ids.dropdown_input(MATCH), "value"),
    )
    def update_graphs_per_activity_type(
        profile_type_valid: str, profile_type_input: str
    ):
        ptype_val = data_utils.ptype_from_label(profile_type_valid)
        ptype_in = data_utils.ptype_from_label(profile_type_input)
        freq = plots.histogram_per_activity(ptype_val, ptype_in, datapaths.freq_dir)
        dur = plots.histogram_per_activity(
            ptype_val, ptype_in, datapaths.duration_dir, True
        )
        prob = plots.prob_curve_per_activity(ptype_val, ptype_in, datapaths.prob_dir)
        kpis = plots.indicator_tables_per_activity(ptype_val, ptype_in)
        if not freq:
            # no data available for this profile type
            return plots.titled_card(plots.replacement_text())
        assert (
            freq.keys()
            == dur.keys()
            == prob.keys()
            == kpis.keys()
            == set(plots.ACTIVITY_ORDER)
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
            for a in plots.ACTIVITY_ORDER
        ]
        return rows
