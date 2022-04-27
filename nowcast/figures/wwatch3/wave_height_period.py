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


"""Produce a figure that shows significant wave height and dominant wave period
at a wave buoy calculated by the SoG WaveWatch3(TM) model,
and observed wave heights and dominant wave periods from the NOAA NDBC
https://www.ndbc.noaa.gov/data/realtime2/ web service.

Testing notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/TestWaveHeightPeriod.ipynb

Development notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/wwatch3/DevelopWaveHeightPeriod.ipynb
"""
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

import matplotlib.dates
import matplotlib.pyplot as plt
import moad_tools.observations
import moad_tools.places
import requests
import xarray
from pandas.plotting import register_matplotlib_converters

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    buoy, wwatch3_dataset_url, figsize=(16, 9), theme=nowcast.figures.website_theme
):
    """Plot significant wave height and dominant wave period calculated
    by the SoG WaveWatch3(TM) model,
    and observed wave heights and dominant wave periods from the NOAA NDBC
    https://www.ndbc.noaa.gov/data/realtime2/ web service for the wave buoy
    at :kbd:`buoy`.

    :arg str buoy: Wave buoy name;
                   must be a key in :py:obj:`moad_tools.places.PLACES`.

    :arg str wwatch3_dataset_url: ERDDAP URL for SalishSeaCast WaveWatch3(TM)
                                  NEMO model fields time series dataset.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(buoy, wwatch3_dataset_url)
    fig, (ax_sig_height, ax_peak_freq) = _prep_fig_axes(figsize, theme)
    _plot_wave_height_time_series(ax_sig_height, buoy, plot_data, theme)
    _wave_height_time_series_labels(ax_sig_height, buoy, plot_data, theme)
    _plot_dominant_period_time_series(ax_peak_freq, buoy, plot_data, theme)
    _dominant_period_time_series_labels(ax_peak_freq, buoy, plot_data, theme)
    return fig


def _prep_plot_data(buoy, wwatch3_dataset_url):
    wwatch3_fields = xarray.open_dataset(wwatch3_dataset_url)
    wwatch3 = xarray.Dataset(
        {
            "wave_height": wwatch3_fields.hs.sel(
                longitude=moad_tools.places.PLACES[buoy]["lon lat"][0] + 360,
                latitude=moad_tools.places.PLACES[buoy]["lon lat"][1],
                method="nearest",
            ),
            "peak_freq": wwatch3_fields.fp.sel(
                longitude=moad_tools.places.PLACES[buoy]["lon lat"][0] + 360,
                latitude=moad_tools.places.PLACES[buoy]["lon lat"][1],
                method="nearest",
            ),
        }
    )
    wwatch3_period = slice(
        str(wwatch3_fields.time.data[0]), str(wwatch3_fields.time.data[-1])
    )
    try:
        obs = moad_tools.observations.get_ndbc_buoy(buoy)
        obs = xarray.Dataset(
            {
                "wave_height": obs.loc[wwatch3_period, "WVHT [m]"],
                "dominant_period": obs.loc[wwatch3_period, "DPD [sec]"],
            }
        )
    except ValueError:
        # No observations available, but we still want to plot the model results
        obs = None
    # Change dataset times to Pacific time zone
    shared.localize_time(wwatch3)
    try:
        shared.localize_time(obs)
    except (IndexError, AttributeError):
        # No observations available, but we still want to plot the model results
        obs = None
    return SimpleNamespace(wwatch3=wwatch3, obs=obs)


def _prep_fig_axes(figsize, theme):
    fig, (ax_sig_height, ax_peak_freq) = plt.subplots(
        2, 1, figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"]
    )
    ax_sig_height.set_facecolor(theme.COLOURS["axes"]["background"])
    ax_peak_freq.set_facecolor(theme.COLOURS["axes"]["background"])
    register_matplotlib_converters()
    fig.autofmt_xdate()
    return fig, (ax_sig_height, ax_peak_freq)


def _plot_wave_height_time_series(ax, buoy, plot_data, theme):
    with suppress(AttributeError):
        plot_data.obs.wave_height.plot(
            ax=ax,
            marker=".",
            linestyle="None",
            label="ECCC Observed",
            markerfacecolor=theme.COLOURS["time series"]["obs wave height"],
            markeredgecolor=theme.COLOURS["time series"]["obs wave height"],
        )
    plot_data.wwatch3.wave_height.plot(
        ax=ax,
        linewidth=2,
        label="WaveWatch3",
        color=theme.COLOURS["time series"]["wave height"],
        alpha=0.8,
    )


def _wave_height_time_series_labels(ax, place, plot_data, theme):
    ax.set_title(
        f"Significant Wave Height at {place}",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlim(
        plot_data.wwatch3.wave_height.time.values[0],
        plot_data.wwatch3.wave_height.time.values[-1],
    )
    ax.set_ylabel(
        "Significant Wave Height [m]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.legend(loc="best", prop=theme.FONTS["legend label small"])
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _plot_dominant_period_time_series(ax, buoy, plot_data, theme):
    with suppress(AttributeError):
        plot_data.obs.dominant_period.plot(
            ax=ax,
            marker=".",
            linestyle="None",
            label="ECCC Observed",
            markerfacecolor=theme.COLOURS["time series"]["obs wave height"],
            markeredgecolor=theme.COLOURS["time series"]["obs wave height"],
        )
    (1 / plot_data.wwatch3.peak_freq).plot(
        ax=ax,
        linewidth=2,
        label="WaveWatch3",
        color=theme.COLOURS["time series"]["wave period"],
        alpha=0.8,
    )


def _dominant_period_time_series_labels(ax, place, plot_data, theme):
    ax.set_title(
        f"Dominant Wave Period at {place}",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlabel(
        f'Time [{plot_data.wwatch3.attrs["tz_name"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_xlim(
        plot_data.wwatch3.peak_freq.time.values[0],
        plot_data.wwatch3.peak_freq.time.values[-1],
    )
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d%b %H:%M"))
    ax.set_ylabel(
        "Dominant Wave Period [s]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.legend(loc="best", prop=theme.FONTS["legend label small"])
    ax.grid(axis="both")
    theme.set_axis_colors(ax)
