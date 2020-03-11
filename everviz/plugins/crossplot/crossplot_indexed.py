import os
import pkg_resources

import dash_html_components as html
import dash_core_components as dcc

from uuid import uuid4
from dash.dependencies import Output, Input
from webviz_config import WebvizPluginABC
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from everviz.data.load_csv.get_data import get_data
from everviz.plugins.crossplot.callback.crossplot_callback import (
    get_graph_line,
    crossplot_update_graph,
)
from everviz.plugins.crossplot._get_indexed_control import _identify_indexed_controls
from everviz.plugins.crossplot.callback.crossplot_indexed_dropdown import (
    dropdown_callback,
)
from everviz.plugins.crossplot.layout.crossplot_layout import get_sidebar_layout
from everviz.plugins.crossplot.set_up_assets import set_up_assets


class CrossplotIndexed(WebvizPluginABC):
    def __init__(self, app, data_path, title="Crossplot"):
        super().__init__()
        self.title = title
        self.graph_id = f"graph-{uuid4()}"
        self.dropdown_x_id = f"dropdown-{uuid4()}"
        self.dropdown_y_id = f"dropdown-{uuid4()}"
        self.axis_type_x_id = f"radio-{uuid4()}"
        self.axis_type_y_id = f"radio-{uuid4()}"
        self.axis_options_x_id = f"radio-{uuid4()}"
        self.axis_options_y_id = f"radio-{uuid4()}"
        self.dropdown_realization_id = f"dropdown-{uuid4()}"
        self.interpolation_id = f"interpolation-{uuid4()}"

        self.data_path = data_path
        self.set_callbacks(app)

        ASSETS_DIR = pkg_resources.resource_filename("everviz", os.path.join("assets"))

        WEBVIZ_ASSETS.add(os.path.join(ASSETS_DIR, "axis_customization.css"))

        # We do this because webwiz currently doesn't give a way to serve
        # css when running in non portable mode.
        set_up_assets(app, ASSETS_DIR)

    def add_webvizstore(self):
        return [(get_data, [{"data_path": self.data_path}])]

    @property
    def layout(self):
        df = get_data(self.data_path)
        dropdown_options = list(_identify_indexed_controls(df.columns.unique()).keys())
        realizations = df.index.values
        axis_type = [(i, i) for i in ["Linear", "Log"]]
        axis_options = ["Normal", "Cumulative"]
        interp_types = [
            ("None", None),
            ("Linear", "linear"),
            ("High value", "hv"),
            ("Low value", "vh"),
        ]

        side_bar_config = [
            (
                "radio",
                {
                    "title": "X-axis",
                    "item_id": self.axis_type_x_id,
                    "options": axis_type,
                },
            ),
            ("radio", {"item_id": self.axis_options_x_id, "options": axis_options},),
            ("dropdown", {"item_id": self.dropdown_x_id, "options": dropdown_options},),
            (
                "radio",
                {
                    "title": "Y-axis",
                    "item_id": self.axis_type_y_id,
                    "options": axis_type,
                },
            ),
            ("radio", {"item_id": self.axis_options_y_id, "options": axis_options},),
            ("dropdown", {"item_id": self.dropdown_y_id, "options": dropdown_options},),
            (
                "radio",
                {
                    "title": "Interpolation type",
                    "item_id": self.interpolation_id,
                    "options": interp_types,
                },
            ),
            (
                "dropdown",
                {
                    "item_id": self.dropdown_realization_id,
                    "options": realizations,
                    "multi": True,
                },
            ),
        ]

        return html.Div(
            [
                html.H1(children=self.title, style={"textAlign": "center"}),
                html.Div(
                    [
                        html.Div(
                            [get_sidebar_layout(side_bar_config)],
                            style={
                                "width": "29%",
                                "display": "inline-block",
                                "vertical-align": "top",
                            },
                        ),
                        html.Div(
                            [dcc.Graph(id=self.graph_id)],
                            style={"width": "69%", "display": "inline-block"},
                        ),
                    ]
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.dropdown_y_id, "options"),
            [Input(self.dropdown_x_id, "value"),],
        )
        def update_dropwdown_y(selected_control):
            df = get_data(self.data_path)
            indexed_controls = _identify_indexed_controls(df.columns.unique())
            return dropdown_callback(selected_control, indexed_controls)

        @app.callback(
            Output(self.dropdown_y_id, "value"), [Input(self.dropdown_y_id, "options")],
        )
        def set_y_val_dropdown(available_options):
            return available_options[0]["value"]

        @app.callback(
            Output(self.graph_id, "figure"),
            [
                Input(self.dropdown_x_id, "value"),
                Input(self.dropdown_y_id, "value"),
                Input(self.dropdown_realization_id, "value"),
                Input(self.axis_type_x_id, "value"),
                Input(self.axis_type_y_id, "value"),
                Input(self.interpolation_id, "value"),
                Input(self.axis_options_x_id, "value"),
                Input(self.axis_options_y_id, "value"),
            ],
        )
        def update_graph(
            xaxis_name,
            yaxis_name,
            realization_nr,
            xaxis_type,
            yaxis_type,
            interpolation_type,
            xaxis_opt,
            yaxis_opt,
        ):
            if isinstance(realization_nr, int):
                realization_nr = [realization_nr]

            df = get_data(self.data_path)
            traces = []
            for realization in realization_nr:
                x_data = df.filter(like=xaxis_name).loc[realization]
                y_data = df.filter(like=yaxis_name).loc[realization]
                mode = "markers" if not interpolation_type else "markers+lines"
                traces.append(
                    get_graph_line(
                        x_data,
                        y_data,
                        xaxis_opt,
                        yaxis_opt,
                        mode=mode,
                        line_shape=interpolation_type,
                        name="Realization: {}".format(realization_nr),
                    )
                )
            return crossplot_update_graph(
                traces, xaxis_name, yaxis_name, xaxis_type, yaxis_type
            )