#  Copyright 2013 – present by the SalishSeaCast Project contributors
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

# SPDX-License-Identifier: Apache-2.0


"""Produce a figure that shows the tidal cycle at Point Atkinson during
a 4 week period centred around a model results period.
The tidal cycle is based on predictions calculated by :program:`ttide`
(https://www.eoas.ubc.ca/~rich/#T_Tide).
Those predictions use Canadian Hydrographic Service (CHS) tidal constituents
and include all tide constituents.
The figure also shows the time period of the model results around which it
is centred.
Text below the tidal cycle graph acknowledges the use of :program:`ttide`.

Testing notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/publish/TestPtAtkinsonTideModule.ipynb
"""
from collections import namedtuple

import matplotlib.pyplot as plt
import pytz
from matplotlib.dates import DateFormatter
from pandas.plotting import register_matplotlib_converters
from salishsea_tools import nc_tools

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    grid_T_hr,
    tidal_predictions,
    timezone,
    figsize=(20, 5),
    theme=nowcast.figures.website_theme,
):
    """Plot the tidal cycle at Point Atkinson during a 4 week period centred
    around the model results in :kbd:`grid_T` with that period indicated on
    the graph.

    :arg grid_T_hr: Hourly tracer results dataset from NEMO.
    :type grid_T_hr: :class:`netCDF4.Dataset`

    :arg str tidal_predictions: Path to directory of tidal prediction file.

    :arg str timezone: Timezone to use for display of model results.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(grid_T_hr, timezone, tidal_predictions)
    fig, ax = _prep_fig_axes(figsize, theme)
    _plot_tide_cycle(ax, plot_data, theme)
    _ax_labels(ax, plot_data, theme)
    _attribution_text(ax, theme)
    return fig


def _prep_plot_data(grid_T_hr, timezone, tidal_predictions):
    results_t_start, results_t_end = nc_tools.timestamp(grid_T_hr, (0, -1))
    ttide = shared.get_tides("Point Atkinson", tidal_predictions)
    ttide.time = ttide.time.dt.tz_convert(pytz.timezone(timezone))
    plot_data = namedtuple("PlotData", "results_t_start, results_t_end, ttide")
    return plot_data(results_t_start.to(timezone), results_t_end.to(timezone), ttide)


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"])
    ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor(theme.COLOURS["axes"]["background"])
    register_matplotlib_converters()
    fig.autofmt_xdate()
    return fig, ax


def _plot_tide_cycle(ax, plot_data, theme, ylims=(-3, 3)):
    ax.plot(
        plot_data.ttide.time,
        plot_data.ttide.pred_all,
        linewidth=2,
        color=theme.COLOURS["time series"]["tidal prediction"],
    )
    ax.plot(
        (plot_data.results_t_start.datetime,) * 2,
        ylims,
        linestyle="solid",
        linewidth=2,
        color=theme.COLOURS["time series"]["datetime line"],
    )
    ax.plot(
        (plot_data.results_t_end.datetime,) * 2,
        ylims,
        linestyle="solid",
        linewidth=2,
        color=theme.COLOURS["time series"]["datetime line"],
    )


def _ax_labels(ax, plot_data, theme):
    t_end = plot_data.results_t_end
    ax.set_title(
        f'Tidal Predictions at Point Atkinson: {t_end.format("DD-MMM-YYYY")}',
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlabel(
        f"Date [{t_end.tzinfo.tzname(t_end.datetime)}]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_xlim(
        plot_data.results_t_start.shift(weeks=-2).datetime,
        plot_data.results_t_end.shift(weeks=2).datetime,
    )
    ax.xaxis.set_major_formatter(DateFormatter("%d-%b-%Y"))
    ax.set_ylabel(
        "Sea Surface Height [m]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_ylim(-3, 3)
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _attribution_text(ax, theme):
    ax.text(
        1.0,
        -0.35,
        "Tidal predictions calculated with t_tide: "
        "https://www.eoas.ubc.ca/~rich/#T_Tide\n"
        "using CHS tidal constituents",
        horizontalalignment="right",
        verticalalignment="top",
        transform=ax.transAxes,
        fontproperties=theme.FONTS["figure annotation small"],
        color=theme.COLOURS["text"]["figure annotation"],
    )
