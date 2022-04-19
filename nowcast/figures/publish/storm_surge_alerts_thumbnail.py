#  Copyright 2013 – present The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Produce a figure that shows a map of the Salish Sea with markers indicating
the risks of high water levels at the Point Atkinson, Victoria, Campbell River,
Nanaimo, and Cherry Point tide gauge locations.
The figure also shows wind vectors that indicate the average wind speed and
direction averaged over the 4 hours preceding the maximum sea surface height
at each location.

The figure is a thumbnail version of the figure produced by
:py:mod:`nowcast.figures.publish.storm_surge_alerts`.
It is intended primarily for use on the Salish Sea Storm Surge Information
Portal page https://salishsea.eos.ubc.ca/storm-surge/.

Testing notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestStormSurgeAlertsThumbnailModule.ipynb
"""
from collections import namedtuple

import arrow
import matplotlib.pyplot as plt
import numpy
from matplotlib import gridspec
from salishsea_tools import places, nc_tools, stormtools, unit_conversions, wind_tools

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    grids_15m,
    weather_path,
    coastline,
    tidal_predictions,
    figsize=(18, 20),
    theme=nowcast.figures.website_theme,
):
    """Plot high water level risk indication markers and 4h average wind
    vectors on a Salish Sea map.

    :arg dict grids_15m: Collection of 15m sea surface height datasets at tide
                         gauge locations,
                         keyed by tide gauge station name.
    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    :arg str tidal_predictions: Path to directory of tidal prediction
                                file.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(grids_15m, tidal_predictions, weather_path)
    fig, (ax_map, ax_no_risk, ax_high_risk, ax_extreme_risk) = _prep_fig_axes(
        figsize, theme
    )
    _plot_alerts_map(ax_map, coastline, plot_data, theme)
    legend_boxes = (ax_no_risk, ax_high_risk, ax_extreme_risk)
    risk_levels = (None, "moderate risk", "extreme risk")
    legend_texts = (
        "No flooding\nrisk",
        "Risk of\nhigh water",
        "Extreme risk\nof flooding",
    )
    for ax, risk_level, text in zip(legend_boxes, risk_levels, legend_texts):
        _plot_legend(ax, risk_level, text, theme)
    return fig


def _prep_plot_data(grids_15m, tidal_predictions, weather_path):
    max_ssh, max_ssh_time, risk_levels = {}, {}, {}
    u_wind_4h_avg, v_wind_4h_avg, max_wind_avg = {}, {}, {}
    for name in places.TIDE_GAUGE_SITES:
        ssh_ts = nc_tools.ssh_timeseries_at_point(grids_15m[name], 0, 0, datetimes=True)
        ttide = shared.get_tides(name, tidal_predictions)
        max_ssh[name], max_ssh_time[name] = shared.find_ssh_max(name, ssh_ts, ttide)
        risk_levels[name] = stormtools.storm_surge_risk_level(
            name, max_ssh[name], ttide
        )
        wind_avg = wind_tools.calc_wind_avg_at_point(
            arrow.get(max_ssh_time[name]),
            weather_path,
            places.PLACES[name]["wind grid ji"],
            avg_hrs=-4,
        )
        u_wind_4h_avg[name], v_wind_4h_avg[name] = wind_avg
        max_wind_avg[name], _ = wind_tools.wind_speed_dir(
            u_wind_4h_avg[name], v_wind_4h_avg[name]
        )
    plot_data = namedtuple(
        "PlotData",
        "ssh_ts, max_ssh, max_ssh_time, risk_levels, "
        "u_wind_4h_avg, v_wind_4h_avg, max_wind_avg",
    )
    return plot_data(
        ssh_ts,
        max_ssh,
        max_ssh_time,
        risk_levels,
        u_wind_4h_avg,
        v_wind_4h_avg,
        max_wind_avg,
    )


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"])
    gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 1], height_ratios=[6, 1])
    gs.update(hspace=0.15, wspace=0.05)
    ax_map = fig.add_subplot(gs[0, :])
    ax_no_risk = fig.add_subplot(gs[1, 0])
    ax_no_risk.set_facecolor(theme.COLOURS["figure"]["facecolor"])
    ax_high_risk = fig.add_subplot(gs[1, 1])
    ax_high_risk.set_facecolor(theme.COLOURS["figure"]["facecolor"])
    ax_extreme_risk = fig.add_subplot(gs[1, 2])
    ax_extreme_risk.set_facecolor(theme.COLOURS["figure"]["facecolor"])
    return fig, (ax_map, ax_no_risk, ax_high_risk, ax_extreme_risk)


def _plot_alerts_map(ax, coastline, plot_data, theme):
    shared.plot_map(ax, coastline)
    for name in places.TIDE_GAUGE_SITES:
        alpha = 0 if numpy.isnan(plot_data.max_ssh[name]) else 0.3
        shared.plot_risk_level_marker(
            ax, name, plot_data.risk_levels[name], "o", 55, alpha, theme
        )
        shared.plot_wind_arrow(
            ax,
            *places.PLACES[name]["lon lat"],
            plot_data.u_wind_4h_avg[name],
            plot_data.v_wind_4h_avg[name],
            theme,
        )
    # Format the axes and make it pretty
    _alerts_map_axis_labels(ax, plot_data.ssh_ts.time[0], theme)
    _alerts_map_wind_legend(ax, theme)
    _alerts_map_geo_labels(ax, theme)


def _alerts_map_axis_labels(ax, date_time, theme):
    ax.set_title(
        f"Marine and Atmospheric Conditions\n {date_time:%A, %B %d, %Y}",
        fontproperties=theme.FONTS["axes title large"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlabel(
        "Longitude [°E]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_ylabel(
        "Latitude [°N]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _alerts_map_wind_legend(ax, theme):
    shared.plot_wind_arrow(ax, -122.5, 50.65, 0, -5, theme)
    ax.text(
        -122.58,
        50.5,
        "Reference: 5 m/s",
        rotation=90,
        fontproperties=theme.FONTS["axes annotation"],
        color=theme.COLOURS["text"]["axes annotation"],
    )
    shared.plot_wind_arrow(ax, -122.75, 50.65, 0, unit_conversions.knots_mps(-5), theme)
    ax.text(
        -122.83,
        50.5,
        "Reference: 5 knots",
        rotation=90,
        fontproperties=theme.FONTS["axes annotation"],
        color=theme.COLOURS["text"]["axes annotation"],
    )
    ax.text(
        -122.85,
        49.9,
        "Winds are 4 hour\n" "average before\n" "maximum water level",
        verticalalignment="top",
        bbox=theme.COLOURS["axes textbox"],
        fontproperties=theme.FONTS["axes annotation"],
        color=theme.COLOURS["text"]["axes annotation"],
    )


def _alerts_map_geo_labels(ax, theme):
    geo_labels = (
        # PLACES key, offset x, y, rotation, text size
        ("Pacific Ocean", 0, 0, 0, "left", "small"),
        ("Neah Bay", -0.04, -0.08, 0, "right", "large"),
        ("Juan de Fuca Strait", 0, 0, -18, "left", "small"),
        ("Puget Sound", 0, 0, -30, "left", "small"),
        ("Strait of Georgia", 0, 0, -20, "left", "small"),
        ("Victoria", -0.04, 0.04, 0, "right", "large"),
        ("Cherry Point", 0.04, 0, 0, "left", "large"),
        ("Point Atkinson", 0.06, 0.16, 0, "left", "large"),
        ("Nanaimo", -0.04, 0, 0, "right", "large"),
        ("Campbell River", -0.04, -0.04, 0, "right", "large"),
        ("British Columbia", 0, 0, 0, "left", "small"),
        ("Washington State", 0, 0, 0, "left", "small"),
    )
    for place, dx, dy, rotation, justify, label_size in geo_labels:
        lon, lat = places.PLACES[place]["lon lat"]
        ax.text(
            lon + dx,
            lat + dy,
            place,
            rotation=rotation,
            horizontalalignment=justify,
            fontproperties=theme.FONTS[f"location label {label_size}"],
        )


def _plot_legend(ax, risk_level, text, theme):
    colour = theme.COLOURS["storm surge risk levels"][risk_level]
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.plot(
        0.2, 0.45, marker="o", markersize=70, markeredgewidth=2, color=colour, alpha=0.6
    )
    colour_name = "yellow" if colour.lower() == "gold" else colour
    ax.text(
        0.4,
        0.2,
        f"{colour_name.title()}:\n{text}",
        transform=ax.transAxes,
        fontproperties=theme.FONTS["legend label large"],
        color=theme.COLOURS["text"]["risk level label"],
    )
    _legend_box_hide_frame(ax, theme)


def _legend_box_hide_frame(ax, theme):
    ax.set_facecolor(theme.COLOURS["figure"]["facecolor"])
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    for spine in ax.spines:
        ax.spines[spine].set_visible(False)
