# Copyright 2013-2016 The Salish Sea MEOPAR contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Produce a figure that shows a map of the Salish Sea with markers indicating
the risks of high water levels at the Point Atkinson, Victoria, Campbel River,
Nanaimo, and Cherry Point tide gauge locations.
The figure also shows wind vectors that indicate the average wind speed and
direction averaged over the 4 hours preceding the maximum sea surface height.
Text below the map provides quantitative information about the maximum water
level, when it occurs, and the 4 hr averaged wind speed, as well as
acknowledgement of data sources.
"""
from collections import namedtuple

import arrow
from matplotlib import gridspec
import matplotlib.pyplot as plt

from salishsea_tools import (
    places,
    nc_tools,
    stormtools,
    unit_conversions,
    wind_tools,
)

from nowcast.figures import shared
import nowcast.figures.website_theme


def storm_surge_alerts(
    bathy, grid_T_hr, grids_15m, weather_path, coastline, tidal_predictions,
    figsize=(18, 20),
    theme=nowcast.figures.website_theme,
):
    """Plot high water level risk indication markers and 4h average wind
    vectors on a Salish Sea map with summary text below.

    :arg bathy: Bathymetry dataset for the Salish Sea NEMO model.
    :type bathy: :py:class:`netCDF4.Dataset`

    :arg grid_T_hr: Hourly tracer results dataset from the Salish Sea NEMO
                    model.
    :type grid_T_hr: :py:class:`netCDF4.Dataset`

    :arg dict grids_15m: Collection of 15m sea surface height datasets at tide
                         gauge locations,
                         keyed by tide gauge station name.
    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    arg str tidal_predications: Path to directory of tidal prediction
                                file.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(grids_15m, tidal_predictions, weather_path)
    fig, (ax_map, ax_pa_info, ax_cr_info, ax_vic_info) = _prep_fig_axes(
        figsize, theme)
    _plot_alerts_map(ax_map, coastline, plot_data, theme)
    info_boxes = (ax_pa_info, ax_cr_info, ax_vic_info)
    info_places = ('Point Atkinson', 'Campbell River', 'Victoria')
    for ax, place in zip(info_boxes, info_places):
        _plot_info_box(ax, place)
    _plot_attribution_text(ax_map, theme)
    return fig


def _prep_plot_data(grids_15m, tidal_predictions, weather_path):
    max_ssh, max_ssh_time, risk_levels = {}, {}, {}
    u_wind_4h_avg, v_wind_4h_avg, max_wind_avg = {}, {}, {}
    for name in places.TIDE_GAUGE_SITES:
        ssh_ts = nc_tools.ssh_timeseries_at_point(
            grids_15m[name], 0, 0, datetimes=True)
        ttide = shared.get_tides(name, tidal_predictions)
        max_ssh[name], max_ssh_time[name] = shared.find_ssh_max(
            name, ssh_ts, ttide)
        risk_levels[name] = stormtools.storm_surge_risk_level(
                     name, max_ssh[name], ttide)
        wind_avg = wind_tools.calc_wind_avg_at_point(
            arrow.get(max_ssh_time[name]), weather_path,
            places.PLACES[name]['wind grid ji'], avg_hrs=-4)
        u_wind_4h_avg[name], v_wind_4h_avg[name] = wind_avg
        max_wind_avg[name], _ = wind_tools.wind_speed_dir(
            u_wind_4h_avg[name], v_wind_4h_avg[name])
    plot_data = namedtuple(
        'PlotData',
        'ssh_ts, max_ssh, max_ssh_time, risk_levels, '
        'u_wind_4h_avg, v_wind_4h_avg, max_wind_avg')
    return plot_data(
        ssh_ts, max_ssh, max_ssh_time, risk_levels,
        u_wind_4h_avg, v_wind_4h_avg, max_wind_avg)


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])
    gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 1], height_ratios=[6, 1])
    gs.update(hspace=0.1, wspace=0.05)
    ax_map = fig.add_subplot(gs[0, :])
    ax_pa_info = fig.add_subplot(gs[1, 0])
    ax_cr_info = fig.add_subplot(gs[1, 1])
    ax_vic_info = fig.add_subplot(gs[1, 2])
    return fig, (ax_map, ax_pa_info, ax_cr_info, ax_vic_info)


def _plot_alerts_map(ax, coastline, plot_data, theme):
    shared.plot_map(ax, coastline)
    for name in places.TIDE_GAUGE_SITES:
        shared.plot_risk_level_marker(
            ax, name, plot_data.risk_levels[name], 'o', 55, 0.3, theme)
        shared.plot_wind_arrow(
            ax, *places.PLACES[name]['lon lat'],
            plot_data.u_wind_4h_avg[name], plot_data.v_wind_4h_avg[name],
            theme)
    # Format the axes and make it pretty
    _alerts_map_axis_labels(ax, plot_data.ssh_ts.time[0], theme)
    _alerts_map_marker_legend(ax, theme)
    _alerts_map_wind_legend(ax, theme)
    _alerts_map_geo_labels(ax, theme)


def _alerts_map_axis_labels(ax, date_time, theme):
    ## TODO: Change all text drawing to use:
    ## prop=theme.FONTS[...], color=THEME.COLOURS['text'][...]
    ax.set_title(
        'Marine and Atmospheric Conditions\n {:%A, %B %d, %Y}'
        .format(date_time),
        **theme.FONTS['axes title'])
    ax.set_xlabel('Longitude [°E]', **theme.FONTS['axis'])
    ax.set_ylabel('Latitude [°N]', **theme.FONTS['axis'])
    ax.text(
        0.4, -0.25,
        'Wind vectors averaged over four hours prior to maximum water level',
        horizontalalignment='left', verticalalignment='top',
        transform=ax.transAxes, **theme.FONTS['figure annotation'])
    ax.grid(axis='both')
    theme.set_axis_colors(ax)


def _alerts_map_marker_legend(ax, theme):
    # This is a bit of a hack. Plot markers at coordinates way outside the
    # axes limits to provide content for the legend.
    risk_levels = (
        # (Risk level key in theme.COLOURS, legend label)
        (None, 'No floosing\nrisk'),
        ('moderate risk', 'Risk of\nhigh water'),
        ('extreme risk', 'Extreme risk\nof flooding'),
    )
    for level, label in risk_levels:
        ax.plot(
            0, 0, marker='o', linestyle='', markersize=25, alpha=0.5,
            color=theme.COLOURS['storm surge risk levels'][level],
            label=label)
    legend = ax.legend(
        numpoints=1, loc='upper left', bbox_to_anchor=(0.9, 1.05),
        prop=theme.FONTS['legend label'])
    legend.set_title(
        ' Possible\nWarnings',
        prop=theme.FONTS['legend title'])


def _alerts_map_wind_legend(ax, theme):
    shared.plot_wind_arrow(ax, -122.5, 50.65, 0, -5, theme)
    ax.text(
        -122.58, 50.5, 'Reference: 5 m/s', rotation=90,
        **theme.FONTS['axes annotation'])
    shared.plot_wind_arrow(
        ax, -122.75, 50.65, 0, unit_conversions.knots_mps(-5), theme)
    ax.text(
        -122.83, 50.5, 'Reference: 5 knots', rotation=90,
        **theme.FONTS['axes annotation'])
    ax.text(
        -122.85, 49.9,
        'Winds are 4 hour\n'
        'average before\n'
        'maximum water level',
        verticalalignment='top',
        bbox=theme.COLOURS['axes textbox'],
        **theme.FONTS['axes annotation'])


def _alerts_map_geo_labels(ax, theme):
    geo_labels = (
        # PLACES key, offset x, y, rotation, text size
        ('Pacific Ocean', 0, 0, 0, 'left', 'small'),
        ('Juan de Fuca Strait', 0, 0, -18, 'left', 'small'),
        ('Puget Sound', 0, 0, -30, 'left', 'small'),
        ('Strait of Georgia', 0, 0, -20, 'left', 'small'),
        ('Victoria', -0.04, 0.04, 0, 'right', 'large'),
        ('Cherry Point', 0.04, 0, 0, 'left', 'large'),
        ('Point Atkinson', 0.06, 0.16, 0, 'left', 'large'),
        ('Nanaimo', -0.04, 0, 0, 'right', 'large'),
        ('Campbell River', -0.04, -0.04, 0, 'right', 'large'),
        ('British Columbia', 0, 0, 0, 'left', 'small'),
        ('Washington State', 0, 0, 0, 'left', 'small'),
    )
    for place, dx, dy, rotation, justify, label_size in geo_labels:
        lon, lat = places.PLACES[place]['lon lat']
        ax.text(
            lon + dx, lat + dy, place, rotation=rotation,
            horizontalalignment=justify,
            fontproperties=theme.FONTS['location label {}'.format(label_size)])


def _plot_info_box(ax, place):
    pass


def _plot_attribution_text(ax, theme):
    ax.text(
        0.4, -0.29,
        'Modelled winds are from the High Resolution Deterministic Prediction '
        'System\n'
        'of Environment Canada: '
        'https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html.',
        horizontalalignment='left', verticalalignment='top',
        transform=ax.transAxes, **theme.FONTS['figure annotation'])
    ax.text(
        0.4, -0.35,
        'Pacific North-West coastline was created from BC Freshwater Atlas '
        'Coastline\n'
        'and WA Marine Shorelines files and compiled by Rich Pawlowicz.',
        horizontalalignment='left', verticalalignment='top',
        transform=ax.transAxes, **theme.FONTS['figure annotation'])
