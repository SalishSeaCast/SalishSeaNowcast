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


"""Produce a figure that shows water levels at a tide gauge station
calculated by the VHFR FVCOM and SalishSeaCast NEMO models,
and predicted and observed water levels from the CHS
``https://ws-shc.qc.dfo-mpo.gc.ca/`` water levels web service.

Testing notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/TestTideStnWaterLevel.ipynb

Development notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/fvcom/publish/DevelopTideStnWaterLevel.ipynb
"""
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import arrow
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy
import requests
import xarray
from pandas.plotting import register_matplotlib_converters
from salishsea_tools import data_tools
from salishsea_tools.places import PLACES

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    place,
    fvcom_ssh_datasets,
    nemo_ssh_dataset_url_tmpl,
    figsize=(16, 9),
    theme=nowcast.figures.website_theme,
):
    """Plot water levels calculated by the VHFR FVCOM and SalishSeaCast NEMO
    models, and predicted and observed water levels from the CHS
    ``https://ws-shc.qc.dfo-mpo.gc.ca/`` water levels web service for the
    tide gauge station at ``place``.

    :arg str place: Tide gauge station name;
                    must be a key in :py:obj:`salishsea_tools.places.PLACES`.

    :arg fvcom_ssh_datasets: Dictionary of VHFR FVCOM model tide gauge station
                             sea surface height time series of
                             py:class:`xarray.Dataset` objects keyed by model
                             model configuration (``x2``, ``r12``).
    :type fvcom_ssh_datasets: :py:class:`dict`

    :arg str nemo_ssh_dataset_url_tmpl: ERDDAP URL template for SalishSeaCast
                                        NEMO model tide gauge station
                                        sea surface height time series dataset.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(place, fvcom_ssh_datasets, nemo_ssh_dataset_url_tmpl)
    fig, (ax_ssh, ax_res) = _prep_fig_axes(figsize, theme)
    _plot_water_level_time_series(ax_ssh, plot_data, theme)
    _water_level_time_series_labels(ax_ssh, plot_data, place, theme)
    _plot_residual_time_series(ax_res, plot_data, theme)
    _residual_time_series_labels(ax_res, plot_data, theme)
    return fig


def _prep_plot_data(place, fvcom_ssh_datasets, nemo_ssh_dataset_url_tmpl):
    # FVCOM sea surface height dataset(s)
    fvcom_sshs = {}
    for model_config, fvcom_ssh_dataset in fvcom_ssh_datasets.items():
        fvcom_sshs[model_config] = fvcom_ssh_dataset.zeta.isel(
            station=[
                name.decode().strip().split(maxsplit=1)[1]
                for name in fvcom_ssh_dataset.name_station.values
            ].index(place)
        )
        # Drop repeated times
        _, index = numpy.unique(fvcom_sshs[model_config].time.values, return_index=True)
        fvcom_sshs[model_config] = fvcom_sshs[model_config].isel(time=index)
    fvcom_period = slice(
        str(fvcom_sshs["x2"].time.values[0]), str(fvcom_sshs["x2"].time.values[-1])
    )
    # NEMO sea surface height dataset
    try:
        nemo_ssh = _get_nemo_ssh(place, nemo_ssh_dataset_url_tmpl).sel(
            time=fvcom_period
        )
    except ValueError:
        # No NEMO sea surface height dataset for place
        nemo_ssh = None
    # CHS water level observations dataset
    try:
        obs_1min = (
            data_tools.get_chs_tides(
                "obs",
                place,
                arrow.get(fvcom_period.start) - timedelta(seconds=5 * 60),
                arrow.get(fvcom_period.stop),
            )
            .to_xarray()
            .rename({"index": "time"})
        )
        obs = obs_1min.to_dataset(name="water_level")
    except (AttributeError, KeyError):
        # No observations available, or invalid tide gauge station number
        obs_1min, obs = None, None
    # CHS water level predictions dataset
    try:
        pred_place = "Point Atkinson" if place == "Sandy Cove" else place
        try:
            pred = (
                data_tools.get_chs_tides(
                    "pred",
                    pred_place,
                    arrow.get(fvcom_period.start),
                    arrow.get(fvcom_period.stop),
                )
                .to_xarray()
                .rename({"index": "time"})
            )
            pred = pred.to_dataset(name="water_level")
        except (AttributeError, KeyError):
            # No predictions available, or invalid tide gauge station number
            pred = None
        # Residual differences between corrected model and observations and predicted tides
        fvcom_residuals = {}
        for model_config, fvcom_ssh in fvcom_sshs.items():
            try:
                fvcom_residuals[model_config] = fvcom_ssh - pred.water_level
                shared.localize_time(fvcom_residuals[model_config])
            except AttributeError:
                fvcom_residuals = None
        try:
            nemo_residual = nemo_ssh.ssh - pred.water_level
            shared.localize_time(nemo_residual)
        except AttributeError:
            nemo_residual = None
        try:
            obs_15min_avg = (obs_1min.resample(time="15min").mean())[1:]
            obs_15min = obs_15min_avg.to_dataset(name="water_level")
            obs_residual = obs_15min.water_level - pred.water_level
            shared.localize_time(obs_residual)
        except AttributeError:
            obs_residual = None
    except (TypeError, IndexError):
        # Invalid tide gauge station number, probably None
        pred, fvcom_residuals, nemo_residual, obs_residual = None, None, None, None
    # Change dataset times to Pacific time zone
    for fvcom_ssh in fvcom_sshs.values():
        shared.localize_time(fvcom_ssh)
    with suppress(IndexError, AttributeError):
        shared.localize_time(nemo_ssh)
    with suppress(IndexError, AttributeError):
        shared.localize_time(obs)
    with suppress(IndexError, AttributeError):
        shared.localize_time(pred)
    # Mean sea level
    msl = PLACES[place]["mean sea lvl"]
    return SimpleNamespace(
        fvcom_sshs=fvcom_sshs,
        nemo_ssh=nemo_ssh,
        obs=obs,
        pred=pred,
        msl=msl,
        fvcom_residuals=fvcom_residuals,
        nemo_residual=nemo_residual,
        obs_residual=obs_residual,
    )


def _get_nemo_ssh(place, dataset_url_tmpl):
    ## TODO: This is a work-around because neither netCDF4 nor xarray are able
    ##       to load the dataset directly from the URL due to an OpenDAP issue
    dataset_url = dataset_url_tmpl.format(place=place.replace(" ", ""))
    dataset_id = dataset_url.rsplit("/", 1)[1]
    ssh_file = Path("/tmp").joinpath(dataset_id).with_suffix(".nc")
    with ssh_file.open("wb") as f:
        resp = requests.get(f"{dataset_url}.nc")
        f.write(resp.content)
    try:
        nemo_ssh = xarray.open_dataset(ssh_file)
    except OSError:
        raise ValueError(f"NEMO ssh dataset not found for {place}")
    return nemo_ssh


def _prep_fig_axes(figsize, theme):
    fig, (ax_ssh, ax_res) = plt.subplots(
        nrows=2, figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"]
    )
    ax_ssh.set_facecolor(theme.COLOURS["axes"]["background"])
    ax_res.set_facecolor(theme.COLOURS["axes"]["background"])
    register_matplotlib_converters()
    fig.autofmt_xdate()
    return fig, (ax_ssh, ax_res)


def _plot_water_level_time_series(ax, plot_data, theme):
    with suppress(AttributeError):
        # CHS sometimes returns an empty observations dataset
        if plot_data.obs.water_level.size:
            plot_data.obs.water_level.plot(
                ax=ax,
                linewidth=2,
                label="CHS Observed",
                color=theme.COLOURS["time series"]["tide gauge obs"],
            )
    with suppress(AttributeError):
        # CHS sometimes returns an empty prediction dataset
        if plot_data.pred.water_level.size:
            plot_data.pred.water_level.plot(
                ax=ax,
                linewidth=2,
                label="CHS Predicted",
                color=theme.COLOURS["time series"]["tidal prediction"],
                alpha=0.8,
            )
    with suppress(AttributeError):
        (plot_data.nemo_ssh.ssh + plot_data.msl).plot(
            ax=ax,
            linewidth=2,
            label="NEMO",
            color=theme.COLOURS["time series"]["tide gauge ssh"],
            alpha=0.8,
        )
    for model_config, fvcom_ssh in plot_data.fvcom_sshs.items():
        (fvcom_ssh + plot_data.msl).plot(
            ax=ax,
            linewidth=2,
            label=f"FVCOM {model_config.upper()}",
            color=theme.COLOURS["time series"]["vhfr fvcom ssh"][model_config],
            alpha=0.8,
        )


def _water_level_time_series_labels(ax, plot_data, place, theme):
    ax.set_title(
        f"Water Level at {place}",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlabel("")
    ax.set_xlim(
        plot_data.fvcom_sshs["x2"].time.values[0],
        plot_data.fvcom_sshs["x2"].time.values[-1],
    )
    ax.set_ylabel(
        "Water Level above Chart Datum [m]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.legend(loc="best", prop=theme.FONTS["legend label small"])
    ax.grid(axis="both")
    theme.set_axis_colors(ax)


def _plot_residual_time_series(ax, plot_data, theme):
    with suppress(AttributeError):
        # CHS sometimes returns an empty observations dataset
        plot_data.obs_residual.plot(
            ax=ax,
            linewidth=2,
            label="CHS Observed",
            color=theme.COLOURS["time series"]["tide gauge obs"],
        )
    with suppress(TypeError):
        # No NEMO residual, probably because place is outside NEMO domaain
        (plot_data.nemo_residual + plot_data.msl).plot(
            ax=ax,
            linewidth=2,
            label="NEMO",
            color=theme.COLOURS["time series"]["tide gauge ssh"],
            alpha=0.8,
        )
    try:
        for model_config, fvcom_residual in plot_data.fvcom_residuals.items():
            (fvcom_residual + plot_data.msl).plot(
                ax=ax,
                linewidth=2,
                label=f"FVCOM {model_config.upper()}",
                color=theme.COLOURS["time series"]["vhfr fvcom ssh"][model_config],
                alpha=0.8,
            )
    except AttributeError:
        # No FVCOM residual, probably because no predicted water level
        # Plot invisible values so that we can label the x-axis, and add "Not Available" text
        ax.plot(
            plot_data.fvcom_sshs["x2"].time,
            numpy.zeros_like(plot_data.fvcom_sshs["x2"]),
            color=theme.COLOURS["axes"]["background"],
        )
        ax.text(
            0.5,
            0.5,
            "Not Available",
            fontproperties=theme.FONTS["axes annotation"],
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
        )


def _residual_time_series_labels(ax, plot_data, theme):
    ax.set_xlabel(
        f'Time [{plot_data.fvcom_sshs["x2"].attrs["tz_name"]}]',
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_xlim(
        plot_data.fvcom_sshs["x2"].time.values[0],
        plot_data.fvcom_sshs["x2"].time.values[-1],
    )
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d%b %H:%M"))
    ax.set_ylabel(
        "Residual [m]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    _, legend_labels = ax.get_legend_handles_labels()
    if legend_labels:
        # Don't try to draw a legend if there is no labels because doing so results in
        # WARNING:matplotlib.legend:No handles with labels found to put in legend.
        ax.legend(loc="best", prop=theme.FONTS["legend label small"])
    ax.grid(axis="both")
    theme.set_axis_colors(ax)
