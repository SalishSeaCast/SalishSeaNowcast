# Copyright 2013-2017 The Salish Sea MEOPAR contributors
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
"""Produce a figure that shows a map of the Salish Sea with coloured contours
showing the sea surface height when it is at its maximum at a specified tide
gauge station.
The figure also shows 24 hour time series graphs of:

* Raw and corrected model water levels compared to the
  tidal prediction for the gauge location

* Water level residuals
  (the difference between the corrected model results and the tidal predictions)

The tidal predictions are calculated by :program:`ttide`
(http://www.eos.ubc.ca/~rich/#T_Tide).
Those predictions use Canadian Hydrographic Service (CHS) tidal constituents
and include all tide constituents.
The corrected model results take into account the errors that result from using
only 8 tidal constituents in the model calculations.

The figure is annotated with the calcualted maximum sea surface height at the
tide gauge location, the time at which it occurs, the ssh residual, and the
wind speed and direction at that time.
"""
from types import SimpleNamespace

import arrow
from matplotlib import gridspec
from matplotlib.dates import DateFormatter
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np
import pytz

from salishsea_tools import (
    nc_tools,
    viz_tools,
    wind_tools,
)
from salishsea_tools.places import PLACES

from nowcast.figures import shared
import nowcast.figures.website_theme


def make_figure(
    place,
    grid_T_hr,
    grids_15m,
    bathy,
    weather_path,
    tidal_predictions,
    timezone,
    figsize=(20, 12),
    theme=nowcast.figures.website_theme
):
    """Plot tidal prediction and models water level timeseries,
    storm surge residual timeseries, sea surface height contours
    on a Salish Sea map, and summary text for the tide gauge station at
    :kbd:`place`.

    :arg str place: Tide gauge station name;
                    must be a key in :py:obj:`salishsea_tools.places.PLACES`.

    :arg grid_T_hr: Hourly averaged tracer results dataset that includes
                    calculated sea surface height.
    :type grid_T_hr: :py:class:`netCDF4.Dataset`

    :arg dict grids_15m: Collection of 15 minute averaged sea surface height
                         datasets at tide gauge locations,
                         keyed by tide gauge station name.

    :arg bathy: Model bathymetry.
    :type bathy: :py:class:`netCDF4.Dataset`

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg str tidal_predictions: Path to directory of tidal prediction file.

    :arg str timezone: Timezone to use for presentation of dates and times;
                       e.g. :kbd:`Canada/Pacific`.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(
        place, grid_T_hr, grids_15m, bathy, timezone, weather_path,
        tidal_predictions
    )
    fig, (ax_info, ax_ssh, ax_map, ax_res) = _prep_fig_axes(figsize, theme)
    _plot_info_box(ax_info, place, plot_data, theme)
    _plot_ssh_time_series(ax_ssh, place, plot_data, timezone, theme)
    _plot_residual_time_series(ax_res, plot_data, timezone, theme)
    _plot_ssh_map(ax_map, plot_data, place, theme)
    return fig


def _prep_plot_data(
    place, grid_T_hr, grids_15m, bathy, timezone, weather_path,
    tidal_predictions
):
    ssh_hr = grid_T_hr.variables['sossheig']
    time_ssh_hr = nc_tools.timestamp(
        grid_T_hr, range(grid_T_hr.variables['time_counter'].size)
    )
    try:
        j, i = PLACES[place]['NEMO grid ji']
    except KeyError as e:
        raise KeyError(
            f'place name or info key not found in '
            f'salishsea_tools.places.PLACES: {e}'
        )
    itime_max_ssh = np.argmax(ssh_hr[:, j, i])
    time_max_ssh_hr = time_ssh_hr[itime_max_ssh]
    ssh_15m_ts = nc_tools.ssh_timeseries_at_point(
        grids_15m[place], 0, 0, datetimes=True
    )
    ttide = shared.get_tides(place, tidal_predictions)
    ssh_corr = shared.correct_model_ssh(ssh_15m_ts.ssh, ssh_15m_ts.time, ttide)

    msl = PLACES[place]['mean sea lvl']
    extreme_ssh = PLACES[place]['hist max sea lvl']
    max_tides = max(ttide.pred_all) + msl
    mid_tides = 0.5 * (extreme_ssh - max_tides) + max_tides
    max_ssh = np.max(ssh_corr) + msl
    thresholds = (max_tides, mid_tides, extreme_ssh)

    max_ssh_15m, time_max_ssh_15m = shared.find_ssh_max(
        place, ssh_15m_ts, ttide
    )
    tides_15m = shared.interp_to_model_time(
        ssh_15m_ts.time, ttide.pred_all, ttide.time
    )
    residual = ssh_corr - tides_15m
    max_ssh_residual = residual[ssh_15m_ts.time == time_max_ssh_15m][0]
    wind_4h_avg = wind_tools.calc_wind_avg_at_point(
        arrow.get(time_max_ssh_15m),
        weather_path,
        PLACES[place]['wind grid ji'],
        avg_hrs=-4
    )
    wind_4h_avg = wind_tools.wind_speed_dir(*wind_4h_avg)
    return SimpleNamespace(
        ssh_max_field=ssh_hr[itime_max_ssh],
        time_max_ssh_hr=time_max_ssh_hr.to(timezone),
        ssh_15m_ts=ssh_15m_ts,
        ssh_corr=ssh_corr,
        max_ssh_15m=max_ssh_15m - PLACES[place]['mean sea lvl'],
        time_max_ssh_15m=arrow.get(time_max_ssh_15m).to(timezone),
        residual=residual,
        max_ssh_residual=max_ssh_residual,
        wind_4h_avg=wind_4h_avg,
        ttide=ttide,
        bathy=bathy,
        thresholds=thresholds,
        msl=msl,
    )


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor']
    )
    gs = gridspec.GridSpec(3, 2, width_ratios=[2, 1])
    gs.update(wspace=0.13, hspace=0.2)
    ax_info = fig.add_subplot(gs[0, 0])

    # Make left axis ax[0] in chart datum and right axis ax[1] in meters above mean sea level
    # Currently, all data belongs to the left axis ax[0]
    # It might be cleaner to have data belong to the right axis and not do as many conversions from meters above sea level to chart datum
    ax_ssh = [0, 0]
    ax_ssh[0] = fig.add_subplot(gs[1, 0])
    ax_ssh[1] = ax_ssh[0].twinx()
    for axis in ax_ssh:
        axis.set_axis_bgcolor(theme.COLOURS['axes']['background'])
    ax_res = fig.add_subplot(gs[2, 0])
    ax_res.set_axis_bgcolor(theme.COLOURS['axes']['background'])
    ax_map = fig.add_subplot(gs[:, 1])
    fig.autofmt_xdate()
    return fig, (ax_info, ax_ssh, ax_map, ax_res)


def _plot_info_box(ax, place, plot_data, theme):
    ax.text(
        0.05,
        0.9,
        place,
        horizontalalignment='left',
        verticalalignment='top',
        transform=ax.transAxes,
        fontproperties=theme.FONTS['info box title'],
        color=theme.COLOURS['text']['info box title']
    )
    ax.text(
        0.05,
        0.75,
        f'Max SSH: {plot_data.max_ssh_15m+plot_data.msl:.2f} metres above chart datum',
        horizontalalignment='left',
        verticalalignment='top',
        transform=ax.transAxes,
        fontproperties=theme.FONTS['info box content'],
        color=theme.COLOURS['text']['info box content']
    )
    time_max_ssh_15m = plot_data.time_max_ssh_15m
    ax.text(
        0.05,
        0.6,
        f'Time of max: {time_max_ssh_15m.format("YYYY-MM-DD HH:mm")} '
        f'{time_max_ssh_15m.datetime.tzname()}',
        horizontalalignment='left',
        verticalalignment='top',
        transform=ax.transAxes,
        fontproperties=theme.FONTS['info box content'],
        color=theme.COLOURS['text']['info box content']
    )
    ax.text(
        0.05,
        0.45,
        f'Residual: {plot_data.max_ssh_residual:.2f} metres',
        horizontalalignment='left',
        verticalalignment='top',
        transform=ax.transAxes,
        fontproperties=theme.FONTS['info box content'],
        color=theme.COLOURS['text']['info box content']
    )
    heading = wind_tools.bearing_heading(
        wind_tools.wind_to_from(plot_data.wind_4h_avg.dir)
    )
    ax.text(
        0.05,
        0.3,
        f'Wind: {plot_data.wind_4h_avg.speed:.0f} m/s from the {heading} \n'
        f'(averaged over four hours prior to maximum water level)',
        horizontalalignment='left',
        verticalalignment='top',
        transform=ax.transAxes,
        fontproperties=theme.FONTS['info box content'],
        color=theme.COLOURS['text']['info box content']
    )
    _info_box_hide_frame(ax, theme)


def _info_box_hide_frame(ax, theme):
    ax.set_axis_bgcolor(theme.COLOURS['figure']['facecolor'])
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    for spine in ax.spines:
        ax.spines[spine].set_visible(False)


def _plot_ssh_time_series(
    ax, place, plot_data, timezone, theme, ylims=(-1, 6)
):
    time = [
        t.astimezone(pytz.timezone(timezone))
        for t in plot_data.ssh_15m_ts.time
    ]

    ax[0].plot(
        plot_data.ttide.time,
        plot_data.ttide.pred_all + plot_data.msl,
        linewidth=2,
        label='Tide Prediction',
        # theme color conflict with theme
        # color=theme.COLOURS['time series']['tidal prediction vs model']
        color='purple'
    )
    ax[0].plot(
        time,
        plot_data.ssh_corr + plot_data.msl,
        linewidth=2,
        linestyle='-',
        label='Corrected model',
        color=theme.COLOURS['time series']['tide gauge ssh']
    )
    ax[0].plot(
        time,
        plot_data.ssh_15m_ts.ssh + plot_data.msl,
        linewidth=1,
        linestyle='--',
        label='Model',
        color=theme.COLOURS['time series']['tide gauge ssh']
    )
    ax[0].plot(
        plot_data.time_max_ssh_15m.datetime,
        plot_data.max_ssh_15m + plot_data.msl,
        marker='o',
        markersize=10,
        markeredgewidth=3,
        label='Maximum SSH',
        color=theme.COLOURS['marker']['max ssh']
    )

    # Add extreme water levels
    colors = ['Gold', 'Red', 'DarkRed']
    labels = ['Maximum tides', 'Extreme water', 'Historical maximum']
    for wlev, color, label in zip(plot_data.thresholds, colors, labels):
        ax[0].axhline(y=wlev, color=color, lw=2, ls='solid', label=label)

    legend = ax[0].legend(
        numpoints=1,
        bbox_to_anchor=(0.75, 1.2),
        loc='lower left',
        borderaxespad=0.,
        prop={'size': 12},
        title=r'Legend'
    )
    legend.get_title().set_fontsize('16')

    ax[0].set_xlim(plot_data.ssh_15m_ts.time[0], plot_data.ssh_15m_ts.time[-1])
    _ssh_time_series_labels(ax, place, plot_data, ylims, theme)


def _ssh_time_series_labels(ax, place, plot_data, ylims, theme):
    ax[0].set_title(
        f'Sea Surface Height at {place}',
        fontproperties=theme.FONTS['axes title'],
        color=theme.COLOURS['text']['axes title']
    )
    ax[0].grid(axis='both')
    ax[0].set_ylim(ylims)

    # Make right axis ax[1] in metres above mean sea level
    ax[1].set_ylim((ylims[0] - plot_data.msl, ylims[1] - plot_data.msl))
    ylabels = [
        'Water Level above \n Chart Datum [m]', 'Water Level wrt MSL [m]'
    ]
    for axis, ylabel in zip(ax, ylabels):
        axis.set_ylabel(
            ylabel,
            fontproperties=theme.FONTS['axis'],
            color=theme.COLOURS['text']['axis']
        )
        theme.set_axis_colors(axis)


def _plot_residual_time_series(
    ax,
    plot_data,
    timezone,
    theme,
    ylims=(-1, 1),
    yticks=np.arange(-1, 1.25, 0.25)
):
    time = [
        t.astimezone(pytz.timezone(timezone))
        for t in plot_data.ssh_15m_ts.time
    ]
    ax.plot(
        time,
        plot_data.residual,
        linewidth=2,
        label='Residual',
        color=theme.COLOURS['time series']['ssh residual']
    )
    ax.legend()
    _residual_time_series_labels(
        ax, ylims, yticks, timezone, time[0].tzname(), theme
    )


def _residual_time_series_labels(ax, ylims, yticks, timezone, tzname, theme):
    ax.set_xlabel(
        f'Date and Time [{tzname}]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.xaxis.set_major_formatter(
        DateFormatter('%d-%b %H:%M', tz=pytz.timezone(timezone))
    )
    ax.set_ylabel(
        'Residual [m]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.set_ylim(ylims)
    ax.set_yticks(yticks)
    ax.grid(axis='both')
    theme.set_axis_colors(ax)


def _plot_ssh_map(ax, plot_data, place, theme):
    contour_intervals = [
        -1, -0.5, 0.5, 1, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.4, 2.6
    ]
    mesh = ax.contourf(
        plot_data.ssh_max_field,
        contour_intervals,
        cmap='YlOrRd',
        extend='both',
        alpha=0.6
    )
    ax.contour(
        plot_data.ssh_max_field,
        contour_intervals,
        colors='black',
        linestyles='--'
    )
    cbar = plt.colorbar(mesh, ax=ax)
    viz_tools.plot_coastline(ax, plot_data.bathy)
    viz_tools.plot_land_mask(ax, plot_data.bathy, color=theme.COLOURS['land'])
    _ssh_map_axis_labels(ax, place, plot_data, theme)
    _ssh_map_cbar_labels(cbar, contour_intervals, theme)


def _ssh_map_axis_labels(ax, place, plot_data, theme):
    time_max_ssh_hr = plot_data.time_max_ssh_hr
    ax.set_title(
        f'Sea Surface Height at {time_max_ssh_hr.format("HH:mm")} '
        f'{time_max_ssh_hr.datetime.tzname()} '
        f'{time_max_ssh_hr.format("DD-MMM-YYYY")}',
        fontproperties=theme.FONTS['axes title'],
        color=theme.COLOURS['text']['axes title']
    )
    j, i = PLACES[place]['NEMO grid ji']
    ax.plot(
        i,
        j,
        marker='o',
        markersize=10,
        markeredgewidth=3,
        color=theme.COLOURS['marker']['place']
    )
    ax.yaxis.set_major_formatter(NullFormatter())
    ax.grid(axis='both')
    theme.set_axis_colors(ax)


def _ssh_map_cbar_labels(cbar, contour_intervals, theme):
    cbar.set_ticks(contour_intervals)
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
    cbar.set_label(
        'Sea Surface Height [m]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
