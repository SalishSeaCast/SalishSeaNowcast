#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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
"""Produce a figure that shows the sea water current at the 2nd Narrows
Ironworkers Memorial Crossing bridge calculated by the VHFR FVCOM model,
the observed current measured by a horizontal ADCP on the bridge piling.

Testing notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/TestSecondNarrowsCurrent.ipynb

Development notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/DevelopSecondNarrowsCurrent.ipynb
"""
from types import SimpleNamespace

import matplotlib.dates
import matplotlib.pyplot as plt
import numpy
from salishsea_tools import unit_conversions
import xarray

from nowcast.figures import shared
import nowcast.figures.website_theme


def make_figure(
    place,
    fvcom_stns_dataset,
    obs_dataset,
    figsize=(16, 9),
    theme=nowcast.figures.website_theme,
):
    """Plot sea water current calculated by the VHFR FVCOM model, and the
    observed current measured by a horizontal ADCP on the 2nd Narrows
    Ironworkers Memorial Crossing bridge piling.

    :arg str place: Horizontal ADCP station name.

    :arg fvcom_stns_dataset: VHFR FVCOM model horizontal ADCP station sea water
                             current time series dataset.
    :type fvcom_stns_dataset: 'py:class:xarray.Dataset`

    :arg obs_dataset: Observed horizontal ADCP station sea water current time series dataset.
    :type obs_dataset: 'py:class:xarray.Dataset`

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(place, fvcom_stns_dataset, obs_dataset)
    fig, (ax_speed, ax_dir, ax_u) = _prep_fig_axes(figsize, theme)
    _plot_current_speed_time_series(ax_speed, plot_data, theme)
    _current_speed_axes_labels(ax_speed, plot_data, theme)
    _plot_current_direction_time_series(ax_dir, plot_data, theme)
    _current_direction_axes_labels(ax_dir, plot_data, theme)
    _plot_u_velocity_time_series(ax_u, plot_data, theme)
    _u_velocity_axes_labels(ax_u, plot_data, theme)
    return fig


def _prep_plot_data(place, fvcom_stns_dataset, obs_dataset):
    # FVCOM velocity component datasets
    stations = [
        name.decode().strip().split(maxsplit=1)[1]
        for name in fvcom_stns_dataset.name_station.values
    ]
    fvcom_u = fvcom_stns_dataset.u.isel(siglay=0, station=stations.index(place))
    fvcom_u.attrs.update({"long_name": "u Velocity", "units": "m/s", "label": "Model"})
    fvcom_v = fvcom_stns_dataset.v.isel(siglay=0, station=stations.index(place))
    # FVCOM current speed and direction
    fvcom_speed = numpy.sqrt(fvcom_u ** 2 + fvcom_v ** 2)
    fvcom_speed.name = "fvcom_current_speed"
    fvcom_speed.attrs.update(
        {"long_name": "Current Speed", "units": "m/s", "label": "Model"}
    )
    direction = numpy.arctan2(fvcom_v, fvcom_u)
    fvcom_dir = numpy.rad2deg(direction + (direction < 0) * 2 * numpy.pi)
    fvcom_dir.name = "fvcom_current_direction"
    fvcom_dir.attrs.update(
        {
            "long_name": "Current To Direction",
            "units": "°CCW from East",
            "label": "Model",
        }
    )
    # HADCP observations dataset
    obs = xarray.Dataset(
        data_vars={
            "speed": (
                {"time": obs_dataset.data_vars["s.time"].size},
                obs_dataset.data_vars["s.speed"],
                obs_dataset.data_vars["s.speed"].attrs,
            ),
            "direction": (
                {"time": obs_dataset.data_vars["s.time"].size},
                obs_dataset.data_vars["s.direction"],
                obs_dataset.data_vars["s.direction"].attrs,
            ),
        },
        coords={"time": obs_dataset.data_vars["s.time"].values},
    )
    fvcom_time_range = slice(
        str(fvcom_speed.time.values[0]), str(fvcom_speed.time.values[-1])
    )
    obs_u = obs.speed.sel(time=fvcom_time_range) * numpy.sin(
        numpy.deg2rad(obs.direction.sel(time=fvcom_time_range))
    )
    obs_u.attrs.update({"label": "HADCP Observed"})
    obs_speed = obs.speed.sel(time=fvcom_time_range)
    obs_speed.attrs.update({"label": "HADCP Observed"})
    rad_ccw_from_east = numpy.deg2rad(90 - obs.direction.sel(time=fvcom_time_range))
    obs_dir = numpy.rad2deg(rad_ccw_from_east + (rad_ccw_from_east < 0) * 2 * numpy.pi)
    obs_dir.attrs.update({"label": "HADCP Observed"})
    for array in (fvcom_u, fvcom_speed, fvcom_dir, obs_u, obs_speed, obs_dir):
        shared.localize_time(array)
    return SimpleNamespace(
        fvcom_u=fvcom_u,
        fvcom_speed=fvcom_speed,
        fvcom_dir=fvcom_dir,
        obs_u=obs_u,
        obs_speed=obs_speed,
        obs_dir=obs_dir,
    )


def _prep_fig_axes(figsize, theme):
    fig, (ax_speed, ax_dir, ax_u) = plt.subplots(
        3, 1, figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"]
    )
    ax_speed = {"mps": ax_speed}
    ax_speed["knots"] = ax_speed["mps"].twinx()
    for ax in ax_speed:
        ax_speed[ax].set_axis_bgcolor(theme.COLOURS["axes"]["background"])
    ax_dir.set_axis_bgcolor(theme.COLOURS["axes"]["background"])
    ax_u = {"mps": ax_u}
    ax_u["knots"] = ax_u["mps"].twinx()
    for ax in ax_u:
        ax_u[ax].set_axis_bgcolor(theme.COLOURS["axes"]["background"])
    fig.autofmt_xdate()
    return fig, (ax_speed, ax_dir, ax_u)


def _plot_current_speed_time_series(ax, plot_data, theme):
    plot_data.obs_speed.plot(
        ax=ax["mps"],
        marker=".",
        linestyle="None",
        label=plot_data.obs_speed.attrs["label"],
        markerfacecolor=theme.COLOURS["time series"][
            "2nd Narrows observed current speed"
        ],
        markeredgecolor=theme.COLOURS["time series"][
            "2nd Narrows observed current speed"
        ],
    )
    plot_data.fvcom_speed.plot(
        ax=ax["mps"],
        linewidth=2,
        color=theme.COLOURS["time series"]["2nd Narrows model current speed"],
        label=plot_data.fvcom_speed.attrs["label"],
        alpha=0.8,
    )


def _current_speed_axes_labels(ax, plot_data, theme):
    ax["mps"].set_title(
        "Current at 2nd Narrows",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    mps_limits = numpy.array((0, 5))
    ax["mps"].set_ylabel(
        f'{plot_data.fvcom_speed.attrs["long_name"]} '
        f'[{plot_data.fvcom_speed.attrs["units"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["mps"].set_ylim(mps_limits)
    ax["knots"].set_ylabel(
        f'{plot_data.fvcom_speed.attrs["long_name"]} [knots]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["knots"].set_ylim(unit_conversions.mps_knots(mps_limits))
    ax["mps"].legend(loc="best")
    ax["mps"].grid(axis="both")
    for k in ax:
        theme.set_axis_colors(ax[k])


def _plot_current_direction_time_series(ax, plot_data, theme):
    plot_data.obs_dir.plot(
        ax=ax,
        marker=".",
        linestyle="None",
        label=plot_data.obs_speed.attrs["label"],
        markerfacecolor=theme.COLOURS["time series"][
            "2nd Narrows observed current direction"
        ],
        markeredgecolor=theme.COLOURS["time series"][
            "2nd Narrows observed current direction"
        ],
    )
    plot_data.fvcom_dir.plot(
        ax=ax,
        linewidth=2,
        color=theme.COLOURS["time series"]["2nd Narrows model current direction"],
        label=plot_data.fvcom_speed.attrs["label"],
        alpha=0.8,
    )


def _current_direction_axes_labels(ax, plot_data, theme):
    ax.set_ylim(0, 360)
    ax.set_yticks((0, 45, 90, 135, 180, 225, 270, 315, 360))
    ax.set_yticklabels(("E", "NE", "N", "NW", "W", "SW", "S", "SE", "E"))
    ax.set_ylabel(
        f'{plot_data.fvcom_dir.attrs["long_name"]} ',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _plot_u_velocity_time_series(ax, plot_data, theme):
    plot_data.obs_u.plot(
        ax=ax["mps"],
        marker=".",
        linestyle="None",
        label=plot_data.obs_u.attrs["label"],
        markerfacecolor=theme.COLOURS["time series"][
            "2nd Narrows observed current speed"
        ],
        markeredgecolor=theme.COLOURS["time series"][
            "2nd Narrows observed current speed"
        ],
    )
    plot_data.fvcom_u.plot(
        ax=ax["mps"],
        linewidth=2,
        color=theme.COLOURS["time series"]["2nd Narrows model current speed"],
        label=plot_data.fvcom_u.attrs["label"],
        alpha=0.8,
    )


def _u_velocity_axes_labels(ax, plot_data, theme):
    ax["mps"].set_xlabel(
        f'Time [{plot_data.fvcom_u.attrs["tz_name"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["mps"].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d%b %H:%M"))
    mps_limits = numpy.array((-5, 5))
    ax["mps"].set_ylabel(
        f'{plot_data.fvcom_u.attrs["long_name"]} '
        f'[{plot_data.fvcom_u.attrs["units"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["mps"].set_ylim(mps_limits)
    ax["knots"].set_ylabel(
        f'{plot_data.fvcom_u.attrs["long_name"]} [knots]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["knots"].set_ylim(unit_conversions.mps_knots(mps_limits))
    ax["mps"].grid(axis="both")
    for k in ax:
        theme.set_axis_colors(ax[k])
