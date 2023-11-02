from pathlib import Path

from dash import html, dcc  # type:ignore
import dash_bootstrap_components as dbc  # type:ignore

from activity_validator.ui import plots, data_utils
from activity_validator.hetus_data_processing.activity_profile import ProfileType


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def create_figure_card(profile_type: ProfileType, path: Path) -> dbc.Card:
    # load the appropriate file depending on the profile type
    filename = path / (profile_type.construct_filename("prob") + ".csv")
    fig = plots.stacked_prob_curves(filename)
    return plots.single_plot_card(data_utils.ptype_to_label(profile_type), fig)


def create_rows_of_cards(path: Path, profile_types, num_columns=4) -> list[dbc.Row]:
    return [
        dbc.Row(
            [dbc.Col([create_figure_card(p, path)], width=3) for p in row]
            + [html.Br()],
            align="center",
            justify="center",
        )
        for row in chunks(profile_types, num_columns)
    ]
