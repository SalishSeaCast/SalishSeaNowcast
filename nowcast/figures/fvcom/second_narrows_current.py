# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
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
"""Produce a figure that shows the sea water current at the 2nd Narrows
Ironworkers Memorial Crossing bridge calculated by the VHFR FVCOM model,
the observed current measured by a horizontal ADCP on the bridge piling.

Testing notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/default/notebooks/figures/fvcom/TestSecondNarrowsCurrent.ipynb

Development notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/default/notebooks/figures/fvcom/DevelopSecondNarrowsCurrent.ipynb
"""
from types import SimpleNamespace

import matplotlib.dates
import matplotlib.pyplot as plt
import numpy
from salishsea_tools import unit_conversions

from nowcast.figures import shared
import nowcast.figures.website_theme


def make_figure(
    place, fvcom_stns_dataset, figsize=(16, 9), theme=nowcast.figures.website_theme
):
    """Plot sea water current calculated by the VHFR FVCOM model, and the
    observed current measured by a horizontal ADCP on the 2nd Narrows
    Ironworkers Memorial Crossing bridge piling.

    :arg str place: Horizontal ADCP station name.

    :arg fvcom_stns_dataset: VHFR FVCOM model horizontal ADCP station sea water
                             current time series dataset.
    :type fvcom_stns_dataset: 'py:class:xarray.Dataset`

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(place, fvcom_stns_dataset)
    fig, (ax_speed, ax_dir, ax_u) = _prep_fig_axes(figsize, theme)
    _plot_current_speed_time_series(ax_speed, plot_data, theme)
    _current_speed_axes_labels(ax_speed, plot_data, theme)
    _plot_current_direction_time_series(ax_dir, plot_data, theme)
    _current_direction_axes_labels(ax_dir, plot_data, theme)
    _plot_u_velocity_time_series(ax_u, plot_data, theme)
    _u_velocity_axes_labels(ax_u, plot_data, theme)
    return fig


def _prep_plot_data(place, fvcom_stns_dataset):
    # FVCOM vertically averaged velocity component datasets
    stations = [
        name.decode().strip().split(maxsplit=1)[1]
        for name in fvcom_stns_dataset.name_station.values
    ]
    fvcom_ua = fvcom_stns_dataset.ua.isel(station=stations.index(place))
    fvcom_ua.attrs.update({"long_name": "u Velocity", "units": "m/s"})
    fvcom_va = fvcom_stns_dataset.va.isel(station=stations.index(place))
    # FVCOM current speed and direction
    fvcom_speed = numpy.sqrt(fvcom_ua ** 2 + fvcom_va ** 2)
    fvcom_speed.name = "fvcom_current_speed"
    fvcom_speed.attrs.update(
        {"long_name": "Current Speed", "units": "m/s", "label": "Model"}
    )
    direction = numpy.arctan2(fvcom_va, fvcom_ua)
    fvcom_dir = numpy.rad2deg(direction + (direction < 0) * 2 * numpy.pi)
    fvcom_dir.name = "fvcom_current_direction"
    fvcom_dir.attrs.update(
        {
            "long_name": "Current To Direction",
            "units": "°CCW from East",
            "label": "Model",
        }
    )
    shared.localize_time(fvcom_ua)
    shared.localize_time(fvcom_speed)
    shared.localize_time(fvcom_dir)
    return SimpleNamespace(
        fvcom_ua=fvcom_ua, fvcom_speed=fvcom_speed, fvcom_dir=fvcom_dir
    )


def _prep_fig_axes(figsize, theme):
    fig, (ax_speed, ax_dir, ax_u) = plt.subplots(
        3, 1, figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"]
    )
    ax_speed = {"mps": ax_speed}
    ax_speed["mps"].set_facecolor(theme.COLOURS["axes"]["background"])
    ax_speed["knots"] = ax_speed["mps"].twinx()
    ax_dir.set_facecolor(theme.COLOURS["axes"]["background"])
    ax_u = {"mps": ax_u}
    ax_u["mps"].set_facecolor(theme.COLOURS["axes"]["background"])
    ax_u["knots"] = ax_u["mps"].twinx()
    fig.autofmt_xdate()
    return fig, (ax_speed, ax_dir, ax_u)


def _plot_current_speed_time_series(ax, plot_data, theme):
    plot_data.fvcom_speed.plot(
        ax=ax["mps"],
        linewidth=2,
        color=theme.COLOURS["time series"]["2nd Narrows model current speed"],
        label=plot_data.fvcom_speed.attrs["label"],
    )


def _current_speed_axes_labels(ax, plot_data, theme):
    ax["mps"].set_title(
        "Current at 2nd Narrows",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax["mps"].set_xlim(
        plot_data.fvcom_speed.time.values[0], plot_data.fvcom_speed.time.values[-1]
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
    plot_data.fvcom_dir.plot(
        ax=ax,
        linewidth=2,
        color=theme.COLOURS["time series"]["2nd Narrows model current direction"],
        label=plot_data.fvcom_speed.attrs["label"],
    )


def _current_direction_axes_labels(ax, plot_data, theme):
    ax.set_xlim(plot_data.fvcom_dir.time.values[0], plot_data.fvcom_dir.time.values[-1])
    ax.set_ylim(0, 360)
    ax.set_yticks((0, 45, 90, 135, 180, 225, 270, 315, 360))
    ax.set_yticklabels(("E", "NE", "N", "NW", "W", "SW", "S", "SE", "E"))
    ax.set_ylabel(
        f'{plot_data.fvcom_dir.attrs["long_name"]} ',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.legend(loc="best")
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _plot_u_velocity_time_series(ax, plot_data, theme):
    plot_data.fvcom_ua.plot(
        ax=ax["mps"],
        linewidth=2,
        color=theme.COLOURS["time series"]["2nd Narrows model current speed"],
    )


def _u_velocity_axes_labels(ax, plot_data, theme):
    ax["mps"].set_xlabel(
        f'Time [{plot_data.fvcom_ua.attrs["tz_name"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["mps"].set_xlim(
        plot_data.fvcom_ua.time.values[0], plot_data.fvcom_ua.time.values[-1]
    )
    ax["mps"].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d%b %H:%M"))
    mps_limits = numpy.array((-4, 4))
    ax["mps"].set_ylabel(
        f'{plot_data.fvcom_ua.attrs["long_name"]} '
        f'[{plot_data.fvcom_ua.attrs["units"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["mps"].set_ylim(mps_limits)
    ax["knots"].set_ylabel(
        f'{plot_data.fvcom_ua.attrs["long_name"]} [knots]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax["knots"].set_ylim(unit_conversions.mps_knots(mps_limits))
    ax["mps"].grid(axis="both")
    for k in ax:
        theme.set_axis_colors(ax[k])
