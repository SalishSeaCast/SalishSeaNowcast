# Copyright 2013-2017 The Salish Sea NEMO Project and
# The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Produce a figure that shows the observed and model forcing wind speed
and direction at Sand Heads during 24 hours of a nowcast run.
Also show a map with the location of Sand Heads marked.
Observations are from Environment and Climate Change Canada data:
http://climate.weather.gc.ca/
Model forcing winds are from the Environment and Climate Change Canada
HRDPS nested model.
Text below the map acknowledges the sources of the observations and HRDPS
product.
"""
from types import SimpleNamespace

from matplotlib import gridspec
import matplotlib.pyplot as plt

from nowcast.figures import shared
import nowcast.figures.website_theme


def make_figure(
    coastline, figsize=(16, 6), theme=nowcast.figures.website_theme
):
    """Plot the time series observed and HRDPS model forcing wind speed and
    direction at Sand Heads.

    :param coastline: Coastline dataset.
    :type coastline: :py:class:`mat.Dataset`

    :param 2-tuple figsize: Figure size (width, height) in inches.

    :param theme: Module-like object that defines the style elements for the
                  figure. See :py:mod:`nowcast.figures.website_theme` for an
                  example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data()
    fig, (ax_speed, ax_dir, ax_map) = _prep_fig_axes(figsize, theme)
    _plot_wind_speed_time_series(ax_speed, plot_data, theme)
    _plot_wind_direction_time_series(ax_dir, plot_data, theme)
    _plot_station_map(ax_map, coastline, theme)
    _attribution_text(ax_map, theme)
    return fig


def _prep_plot_data():
    return SimpleNamespace


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor']
    )
    gs = gridspec.GridSpec(2, 2, width_ratios=[1.618, 1])
    gs.update(wspace=0.23, hspace=0.1)
    ax_speed = {'mps': fig.add_subplot(gs[0, 0])}
    ax_speed['knots'] = ax_speed['mps'].twinx()
    ax_dir = fig.add_subplot(gs[1, 0])
    ax_map = fig.add_subplot(gs[:, 1])
    return fig, (ax_speed, ax_dir, ax_map)


def _plot_wind_speed_time_series(ax, plot_data, theme):
    _wind_speed_axes_labels(ax, theme)


def _wind_speed_axes_labels(ax, theme):
    ax['mps'].set_title(
        'Winds at Sand Heads',
        fontproperties=theme.FONTS['axes title'],
        color=theme.COLOURS['text']['axes title']
    )
    ax['mps'].set_ylabel(
        'Wind Speed [m/s]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax['knots'].set_ylabel(
        'Wind Speed [knots]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    for k in ax:
        ax[k].set_xticklabels([])
        ax[k].grid(axis='both')
        theme.set_axis_colors(ax[k])


def _plot_wind_direction_time_series(ax, plot_data, theme):
    _wind_direction_axes_labels(ax, theme)


def _wind_direction_axes_labels(ax, theme):
    ax.set_xlabel(
        'Time [xxx]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.set_ylim(0, 360)
    ax.set_yticks((0, 45, 90, 135, 180, 225, 270, 315, 360))
    ax.set_ylabel(
        'Wind To Direction\n[Degrees CCW of East]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.grid(axis='both')
    theme.set_axis_colors(ax)


def _plot_station_map(ax, coastline, theme):
    shared.plot_map(ax, coastline)
    _station_map_axes_labels(ax, theme)


def _station_map_axes_labels(ax, theme):
    ax.set_title(
        'Station Location',
        fontproperties=theme.FONTS['axes title'],
        color=theme.COLOURS['text']['axes title']
    )
    ax.set_xlabel(
        'Longitude [°E]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.set_ylabel(
        'Latitude [°N]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.grid(axis='both')
    theme.set_axis_colors(ax)


def _attribution_text(ax_map, theme):
    pass
