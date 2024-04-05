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
"""Produce a 2-panel figure that shows time series of temperature and salinity observations and
model run results at an Ocean Networks Canada (ONC) Salish Sea (VENUS) node.

Testing notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/comparison/TestCompareVENUS_CTD.ipynb
"""
import os
from collections import namedtuple

import matplotlib.pyplot as plt
import numpy as np
import pytz
from matplotlib.dates import DateFormatter
from salishsea_tools import data_tools, places, nc_tools, teos_tools

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    node_name,
    grid_T_hr,
    dev_grid_T_hr,
    timezone,
    mesh_mask,
    dev_mesh_mask,
    figsize=(8, 10),
    theme=nowcast.figures.website_theme,
):
    """Plot the temperature and salinity time series of observations and model
    results at an ONC VENUS node.

    :arg str node_name: Ocean Networks Canada (ONC) VENUS node name;
                        must be a key in
                        :py:obj:`salishsea_tools.places.PLACES`.

    :arg grid_T_hr: Hourly tracer results dataset from production NEMO run.
    :type grid_T_hr: :class:`netCDF4.Dataset`

    :arg dev_grid_T_hr: Hourly tracer results dataset from development NEMO run.
    :type dev_grid_T_hr: :class:`netCDF4.Dataset`

    :arg str timezone: Timezone to use for display of model results.

    :arg mesh_mask: NEMO mesh mask for production NEMO run.
    :type mesh_mask: :class:`netCDF4.Dataset`

    :arg dev_mesh_mask: NEMO mesh mask for development NEMO run.
    :type dev_mesh_mask: :class:`netCDF4.Dataset`

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(
        node_name, grid_T_hr, dev_grid_T_hr, timezone, mesh_mask, dev_mesh_mask
    )
    fig, (ax_sal, ax_temp) = _prep_fig_axes(figsize, theme)
    _plot_salinity_time_series(ax_sal, node_name, plot_data, theme)
    _plot_temperature_time_series(ax_temp, plot_data, timezone, theme)
    _attribution_text(ax_temp, theme)
    return fig


def _prep_plot_data(
    place, grid_T_hr, dev_grid_T_hr, timezone, mesh_mask, dev_mesh_mask
):
    try:
        j, i = places.PLACES[place]["NEMO grid ji"]
    except KeyError as e:
        raise KeyError(
            "place name or info key not found in salishsea_tools.places.PLACES: {e}"
        )
    node_depth = places.PLACES[place]["depth"]
    station_code = places.PLACES[place]["ONC stationCode"]
    # Production model results
    model_time = nc_tools.timestamp(
        grid_T_hr, range(grid_T_hr.variables["time_counter"].size)
    )
    try:
        # NEMO-3.4 mesh mask
        gdept = mesh_mask.variables["gdept"]
    except KeyError:
        # NEMO-3.6 mesh mask
        gdept = mesh_mask.variables["gdept_0"]
    tracer_depths = gdept[..., j, i][0]
    tracer_mask = mesh_mask.variables["tmask"][..., j, i][0]
    try:
        # NEMO-3.4 mesh mask
        gdepw = mesh_mask.variables["gdepw"]
    except KeyError:
        # NEMO-3.6 mesh mask
        gdepw = mesh_mask.variables["gdepw_0"]
    w_depths = gdepw[..., j, i][0]
    salinity_profiles = grid_T_hr.variables["vosaline"][..., j, i]
    temperature_profiles = grid_T_hr.variables["votemper"][..., j, i]
    model_salinity_ts = _calc_results_time_series(
        salinity_profiles,
        model_time,
        node_depth,
        timezone,
        tracer_depths,
        tracer_mask,
        w_depths,
    )
    model_temperature_ts = _calc_results_time_series(
        temperature_profiles,
        model_time,
        node_depth,
        timezone,
        tracer_depths,
        tracer_mask,
        w_depths,
    )
    # Development model results
    if dev_grid_T_hr is None:
        dev_model_salinity_ts, dev_model_temperature_ts = None, None
    else:
        dev_model_time = nc_tools.timestamp(
            dev_grid_T_hr, range(grid_T_hr.variables["time_counter"].size)
        )
        tracer_depths = dev_mesh_mask.variables["gdept_0"][..., j, i][0]
        tracer_mask = dev_mesh_mask.variables["tmask"][..., j, i][0]
        w_depths = dev_mesh_mask.variables["gdepw_0"][..., j, i][0]
        salinity_profiles = dev_grid_T_hr.variables["vosaline"][..., j, i]
        temperature_profiles = dev_grid_T_hr.variables["votemper"][..., j, i]
        dev_model_salinity_ts = _calc_results_time_series(
            salinity_profiles,
            dev_model_time,
            node_depth,
            timezone,
            tracer_depths,
            tracer_mask,
            w_depths,
        )
        dev_model_temperature_ts = _calc_results_time_series(
            temperature_profiles,
            dev_model_time,
            node_depth,
            timezone,
            tracer_depths,
            tracer_mask,
            w_depths,
        )
    # Observations
    onc_data = data_tools.get_onc_data(
        "scalardata",
        "getByLocation",
        os.environ["ONC_USER_TOKEN"],
        locationCode=station_code,
        deviceCategoryCode="CTD",
        sensorCategoryCodes="salinity,temperature",
        dateFrom=data_tools.onc_datetime(model_time[0], "utc"),
        dateTo=data_tools.onc_datetime(model_time[-1], "utc"),
    )
    plot_data = namedtuple(
        "PlotData",
        "model_salinity_ts, model_temperature_ts, "
        "dev_model_salinity_ts, dev_model_temperature_ts, "
        "ctd_data",
    )
    return plot_data(
        model_salinity_ts=model_salinity_ts,
        model_temperature_ts=model_temperature_ts,
        dev_model_salinity_ts=dev_model_salinity_ts,
        dev_model_temperature_ts=dev_model_temperature_ts,
        ctd_data=data_tools.onc_json_to_dataset(onc_data),
    )


def _calc_results_time_series(
    tracer,
    model_time,
    node_depth,
    timezone,
    tracer_depths,
    tracer_mask,
    w_depths,
    psu_to_teos=False,
):
    time_series = namedtuple("TimeSeries", "var, time")
    if psu_to_teos:
        var = teos_tools.psu_teos(
            [
                shared.interpolate_tracer_to_depths(
                    tracer[i, :], tracer_depths, node_depth, tracer_mask, w_depths
                )
                for i in range(tracer.shape[0])
            ]
        )
    else:
        var = [
            shared.interpolate_tracer_to_depths(
                tracer[i, :], tracer_depths, node_depth, tracer_mask, w_depths
            )
            for i in range(tracer.shape[0])
        ]
    return time_series(var=var, time=[t.to(timezone) for t in model_time])


def _prep_fig_axes(figsize, theme):
    fig, (ax_sal, ax_temp) = plt.subplots(
        2,
        1,
        figsize=figsize,
        sharex=True,
        facecolor=theme.COLOURS["figure"]["facecolor"],
    )
    fig.autofmt_xdate()
    ax_sal.set_facecolor(theme.COLOURS["axes"]["background"])
    ax_temp.set_facecolor(theme.COLOURS["axes"]["background"])
    return fig, (ax_sal, ax_temp)


def _plot_salinity_time_series(ax, place, plot_data, theme):
    ctd_data = plot_data.ctd_data
    qaqc_mask = ctd_data.salinity.attrs["qaqcFlag"] == 1
    ax.plot(
        ctd_data.salinity.sampleTime[qaqc_mask],
        ctd_data.salinity[qaqc_mask],
        linewidth=2,
        label="Observations",
        color=theme.COLOURS["time series"]["VENUS CTD salinity"],
    )
    ax.plot(
        [t.datetime for t in plot_data.model_salinity_ts.time],
        plot_data.model_salinity_ts.var,
        linewidth=2,
        label="Model",
        color=theme.COLOURS["time series"]["VENUS node model salinity"],
        alpha=0.7,
    )
    if plot_data.dev_model_salinity_ts is not None:
        ax.plot(
            [t.datetime for t in plot_data.dev_model_salinity_ts.time],
            plot_data.dev_model_salinity_ts.var,
            linewidth=2,
            label="Dev Model",
            color=theme.COLOURS["time series"]["VENUS node dev model salinity"],
            alpha=0.5,
        )
    _salinity_axis_labels(ax, place, plot_data, theme)


def _salinity_axis_labels(ax, place, plot_data, theme):
    first_model_day = plot_data.model_salinity_ts.time[0]
    last_model_day = plot_data.model_salinity_ts.time[-1]
    title_dates = first_model_day.format("DD-MMM-YYYY")
    if first_model_day.day != last_model_day.day:
        title_dates = " and ".join((title_dates, last_model_day.format("DD-MMM-YYYY")))
    ax.set_title(
        f'VENUS {place.title()} {places.PLACES[place]["depth"]}m {title_dates}',
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlim(
        plot_data.model_salinity_ts.time[0].datetime,
        plot_data.model_salinity_ts.time[-1].datetime,
    )
    ax.set_ylabel(
        "Salinity [g/kg]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(np.floor(ymin) - 1, np.ceil(ymax) + 1)
    ax.legend(loc="best")
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _plot_temperature_time_series(ax, plot_data, timezone, theme):
    ctd_data = plot_data.ctd_data
    qaqc_mask = ctd_data.salinity.attrs["qaqcFlag"] == 1
    ax.plot(
        ctd_data.temperature.sampleTime[qaqc_mask],
        ctd_data.temperature[qaqc_mask],
        linewidth=2,
        label="Observations",
        color=theme.COLOURS["time series"]["VENUS CTD temperature"],
    )
    ax.plot(
        [t.datetime for t in plot_data.model_temperature_ts.time],
        plot_data.model_temperature_ts.var,
        linewidth=2,
        label="Model",
        color=theme.COLOURS["time series"]["VENUS node model temperature"],
        alpha=0.7,
    )
    if plot_data.dev_model_salinity_ts is not None:
        ax.plot(
            [t.datetime for t in plot_data.dev_model_temperature_ts.time],
            plot_data.dev_model_temperature_ts.var,
            linewidth=2,
            label="Dev Model",
            color=theme.COLOURS["time series"]["VENUS node dev model temperature"],
            alpha=0.5,
        )
    tzname = plot_data.model_temperature_ts.time[0].datetime.tzname()
    _temperature_axis_labels(ax, plot_data, timezone, tzname, theme)


def _temperature_axis_labels(ax, plot_data, timezone, tzname, theme):
    ax.set_xlabel(
        f"Date and Time [{tzname}]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_xlim(
        plot_data.model_temperature_ts.time[0].datetime,
        plot_data.model_temperature_ts.time[-1].datetime,
    )
    ax.xaxis.set_major_formatter(
        DateFormatter("%d-%b %H:%M", tz=pytz.timezone(timezone))
    )
    ax.set_ylabel(
        "Temperature [°C]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(np.floor(ymin) - 1, np.ceil(ymax) + 1)
    ax.legend(loc="best")
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _attribution_text(ax, theme):
    ax.text(
        1,
        -0.35,
        "Observations from Ocean Networks Canada",
        horizontalalignment="right",
        verticalalignment="top",
        transform=ax.transAxes,
        fontproperties=theme.FONTS["figure annotation small"],
        color=theme.COLOURS["text"]["figure annotation"],
    )
