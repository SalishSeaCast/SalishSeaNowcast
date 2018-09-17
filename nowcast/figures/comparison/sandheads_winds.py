# Copyright 2013-2018 The Salish Sea NEMO Project and
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

import matplotlib.pyplot as plt
import numpy
import xarray
from matplotlib import gridspec
import matplotlib.dates
from salishsea_tools import stormtools, unit_conversions
from salishsea_tools.places import PLACES

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    hrdps_dataset_url,
    run_type,
    run_date,
    coastline,
    figsize=(16, 7),
    theme=nowcast.figures.website_theme,
):
    """Plot the time series observed and HRDPS model forcing wind speed and
    direction at Sand Heads.

    :param str hrdps_dataset_url: ERDDAP dataset URL for the HRDPS product
                                  to be plotted.

    :param str run_type: Type of run to produce figure for.

    :param run_date: Date of the run to create the figure for.
    :type run_date: :py:class:`Arrow.arrow`

    :param coastline: Coastline dataset.
    :type coastline: :py:class:`mat.Dataset`

    :param 2-tuple figsize: Figure size (width, height) in inches.

    :param theme: Module-like object that defines the style elements for the
                  figure. See :py:mod:`nowcast.figures.website_theme` for an
                  example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(hrdps_dataset_url, run_type, run_date)
    fig, (ax_speed, ax_dir, ax_map) = _prep_fig_axes(figsize, theme)
    _plot_wind_speed_time_series(ax_speed, plot_data, theme)
    _plot_wind_direction_time_series(ax_dir, plot_data, theme)
    # Adjust axes labels to accommodate dates/times
    # This turns off *all* x-axes labels, so we do it here in order to be
    # able to turn the labels back on for the map axes
    fig.autofmt_xdate()
    _plot_station_map(ax_map, coastline, theme)
    _attribution_text(ax_map, theme)
    return fig


def _prep_plot_data(hrdps_dataset_url, run_type, run_date):
    hrdps = xarray.open_dataset(hrdps_dataset_url)
    j, i = PLACES["Sand Heads"]["GEM2.5 grid ji"]
    u_hrdps = hrdps.u_wind.sel(time=run_date.format("YYYY-MM-DD")).isel(
        gridY=j, gridX=i
    )
    v_hrdps = hrdps.v_wind.sel(time=run_date.format("YYYY-MM-DD")).isel(
        gridY=j, gridX=i
    )
    hrdps_speed = numpy.sqrt(u_hrdps ** 2 + v_hrdps ** 2)
    hrdps_speed.name = "hrdps_wind_speed"
    hrdps_speed.attrs.update(
        {"long_name": "Wind Speed", "units": "m/s", "label": "Model"}
    )
    shared.localize_time(hrdps_speed)
    direction = numpy.arctan2(v_hrdps, u_hrdps)
    hrdps_dir = numpy.rad2deg(direction + (direction < 0) * 2 * numpy.pi)
    hrdps_dir.name = "hrdps_wind_direction"
    hrdps_dir.attrs.update(
        {"long_name": "Wind To Direction", "units": "°CCW from East", "label": "Model"}
    )
    shared.localize_time(hrdps_dir)
    if run_type.startswith("forecast"):
        return SimpleNamespace(hrdps_speed=hrdps_speed, hrdps_dir=hrdps_dir)
    ec_speed, ec_dir, _, ec_time, _, _ = stormtools.get_EC_observations(
        "Sandheads", run_date.format("DD-MMM-YYYY"), run_date.format("DD-MMM-YYYY")
    )
    obs_speed = xarray.DataArray(
        name="obs_wind_speed",
        data=ec_speed,
        coords={"time": numpy.array(ec_time, dtype="datetime64[ns]")},
        dims=("time",),
        attrs={"long_name": "Wind Speed", "units": "m/s", "label": "Observations"},
    )
    shared.localize_time(obs_speed)
    obs_dir = xarray.DataArray(
        name="obs_wind_direction",
        data=ec_dir,
        coords={"time": numpy.array(ec_time, dtype="datetime64[ns]")},
        dims=("time",),
        attrs={
            "long_name": "Wind To Direction",
            "units": "°CCW from East",
            "label": "Observations",
        },
    )
    shared.localize_time(obs_dir)
    return SimpleNamespace(
        hrdps_speed=hrdps_speed,
        hrdps_dir=hrdps_dir,
        obs_speed=obs_speed,
        obs_dir=obs_dir,
    )


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"])
    gs = gridspec.GridSpec(2, 2, width_ratios=[1.618, 1])
    gs.update(wspace=0.23, hspace=0.15)
    ax_speed = {"mps": fig.add_subplot(gs[0, 0])}
    ax_speed["knots"] = ax_speed["mps"].twinx()
    ax_dir = fig.add_subplot(gs[1, 0])
    ax_map = fig.add_subplot(gs[:, 1])
    return fig, (ax_speed, ax_dir, ax_map)


def _plot_wind_speed_time_series(ax, plot_data, theme):
    plot_data.hrdps_speed.plot(
        ax=ax["mps"],
        linewidth=2,
        color=theme.COLOURS["time series"]["Sand Heads HRDPS wind speed"],
        label=plot_data.hrdps_speed.attrs["label"],
    )
    try:
        plot_data.obs_speed.plot(
            ax=ax["mps"],
            linewidth=2,
            color=theme.COLOURS["time series"]["Sand Heads observed wind speed"],
            label=plot_data.obs_speed.attrs["label"],
        )
    except AttributeError:
        # No observations available
        pass
    _wind_speed_axes_labels(ax, plot_data, theme)


def _wind_speed_axes_labels(ax, plot_data, theme):
    ax["mps"].set_title(
        "Winds at Sand Heads",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    mps_limits = numpy.array((0, 20))
    ax["mps"].set_ylabel(
        f'{plot_data.hrdps_speed.attrs["long_name"]} '
        f'[{plot_data.hrdps_speed.attrs["units"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["mps"].set_ylim(mps_limits)
    ax["knots"].set_ylabel(
        f'{plot_data.hrdps_speed.attrs["long_name"]} [knots]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["knots"].set_ylim(unit_conversions.mps_knots(mps_limits))
    ax["mps"].legend(loc="best")
    ax["mps"].grid(axis="both")
    for k in ax:
        theme.set_axis_colors(ax[k])


def _plot_wind_direction_time_series(ax, plot_data, theme):
    plot_data.hrdps_dir.plot(
        ax=ax,
        linewidth=2,
        color=theme.COLOURS["time series"]["Sand Heads HRDPS wind direction"],
        label=plot_data.hrdps_dir.attrs["label"],
    )
    try:
        plot_data.obs_dir.plot(
            ax=ax,
            linewidth=2,
            color=theme.COLOURS["time series"]["Sand Heads observed wind direction"],
            label=plot_data.obs_dir.attrs["label"],
        )
    except AttributeError:
        # No observations available
        pass
    _wind_direction_axes_labels(ax, plot_data, theme)


def _wind_direction_axes_labels(ax, plot_data, theme):
    ax.set_title("")
    ax.set_xlabel(
        f'Time [{plot_data.hrdps_dir.attrs["tz_name"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d%b %H:%M"))
    ax.set_ylim(0, 360)
    ax.set_yticks((0, 45, 90, 135, 180, 225, 270, 315, 360))
    ax.set_yticklabels(("E", "NE", "N", "NW", "W", "SW", "S", "SE", "E"))
    ax.set_ylabel(
        f'{plot_data.hrdps_dir.attrs["long_name"]} ',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.legend(loc="best")
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _plot_station_map(ax, coastline, theme):
    shared.plot_map(ax, coastline)
    ax.plot(
        *PLACES["Sand Heads"]["lon lat"],
        marker="o",
        markersize=10,
        markeredgewidth=3,
        color=theme.COLOURS["marker"]["place"],
    )
    _station_map_axes_labels(ax, theme)


def _station_map_axes_labels(ax, theme):
    ax.set_title(
        "Station Location",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xticks((-125.5, -124.5, -123.5, -122.5))
    for tick in ax.get_xticklabels():
        tick.set_visible(True)
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


def _attribution_text(ax, theme):
    ax.text(
        -0.15,
        -0.25,
        "Observations from Environment and Climate Change Canada data\n"
        "http://climate.weather.gc.ca/ \n"
        "Modelled winds are from the High Resolution Deterministic Prediction\n"
        "System (HRDPS) of Environment and Climate Change "
        "Canada\n"
        "https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax.transAxes,
        fontproperties=theme.FONTS["figure annotation small"],
        color=theme.COLOURS["text"]["figure annotation"],
    )
