"""
Functions for combining multiple figures in a specific layout, e.g., for an overview.
"""

from pathlib import Path
from plotly.graph_objects import Figure  # type: ignore

from dash import html  # type:ignore
import dash_bootstrap_components as dbc  # type:ignore

from activity_validator.ui import plots, data_utils
from activity_validator.profile_category import ProfileType


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def rows_of_cards(figures: dict[str, Figure], num_columns=4) -> list[dbc.Row]:
    return [
        dbc.Row(
            [
                dbc.Col([plots.single_plot_card(fig, title)], width=3)
                for title, fig in row
            ]
            + [html.Br()],
            align="center",
            justify="center",
            className="mb-3",
        )
        for row in chunks(list(figures.items()), num_columns)
    ]


def create_stacked_prob_curves(paths: dict[str, Path]) -> dict[str, Figure]:
    return {title: plots.stacked_prob_curves(path) for title, path in paths.items()}
