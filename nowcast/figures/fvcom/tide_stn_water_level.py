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
"""Produce a figure that shows water levels at a tide gauge station
calculated by the VHFR FVCOM and SalishSeaCast NEMO models,
and predicted and observed water levels from the CHS
https://ws-shc.qc.dfo-mpo.gc.ca/ water levels web service.

Testing notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/TestTideStnWaterLevel.ipynb

Development notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/DevelopTideStnWaterLevel.ipynb
"""
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import arrow
import matplotlib.dates
import matplotlib.pyplot as plt
import requests
from salishsea_tools import data_tools
from salishsea_tools.places import PLACES
import xarray

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    place,
    fvcom_ssh_dataset,
    nemo_ssh_dataset_url_tmpl,
    figsize=(16, 9),
    theme=nowcast.figures.website_theme
):
    """Plot water levels calculated by the VHFR FVCOM and SalishSeaCast NEMO
    models, and predicted and observed water levels from the CHS
    https://ws-shc.qc.dfo-mpo.gc.ca/ water levels web service for the
    tide gauge station at :kbd:`place`.

    :arg str place: Tide gauge station name;
                    must be a key in :py:obj:`salishsea_tools.places.PLACES`.

    :arg fvcom_ssh_dataset: VHFR FVCOM model tide gauge station sea surface
                            height time series dataset.
    :type fvcom_ssh_dataset: 'py:class:xarray.Dataset`

    :arg str nemo_ssh_dataset_url_tmpl: ERDDAP URL template for SalishSeaCast
                                        NEMO model tide gauge station
                                        sea surface height time series dataset.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(
        place, fvcom_ssh_dataset, nemo_ssh_dataset_url_tmpl
    )
    fig, ax = _prep_fig_axes(figsize, theme)
    _plot_water_level_time_series(ax, place, plot_data, theme)
    return fig


def _prep_plot_data(place, fvcom_ssh_dataset, nemo_ssh_dataset_url_tmpl):
    # FVCOM sea surface height dataset
    fvcom_ssh = fvcom_ssh_dataset.zeta.isel(
        station=[
            name.decode().strip().split(maxsplit=1)[1]
            for name in fvcom_ssh_dataset.name_station.values
        ].index(place)
    )
    fvcom_period = slice(
        str(fvcom_ssh.time.values[0]), str(fvcom_ssh.time.values[-1])
    )
    # NEMO sea surface height dataset
    try:
        nemo_ssh = _get_nemo_ssh(place, nemo_ssh_dataset_url_tmpl
                                 ).sel(time=fvcom_period)
    except ValueError:
        # No NEMO sea surface height dataset for place
        nemo_ssh = None
    # CHS water level observations dataset
    try:
        obs_1min = data_tools.get_chs_tides(
            'obs',
            place,
            arrow.get(fvcom_period.start) - timedelta(seconds=5 * 60),
            arrow.get(fvcom_period.stop)
        )
        obs_10min_avg = xarray.DataArray(
            obs_1min.resample('10min', loffset='5min').mean()
        )
        obs = xarray.Dataset({
            'water_level': obs_10min_avg.rename({
                'dim_0': 'time'
            })
        })
    except TypeError:
        # Invalid tide gauge station number, probably None
        obs = None
    # CHS water level predictions dataset
    try:
        pred_place = 'Point Atkinson' if place == 'Sandy Cove' else place
        pred = data_tools.get_chs_tides(
            'pred', pred_place, arrow.get(fvcom_period.start),
            arrow.get(fvcom_period.stop)
        )
        pred = xarray.Dataset({
            'water_level':
                xarray.DataArray.from_series(pred).rename({
                    'index': 'time'
                })
        })
    except TypeError:
        # Invalid tide gauge station number, probably None
        pred = None
    # Change dataset times to Pacific time zone
    shared.localize_time(fvcom_ssh)
    with suppress(AttributeError):
        shared.localize_time(nemo_ssh)
    with suppress(IndexError, AttributeError):
        shared.localize_time(obs)
    with suppress(IndexError, AttributeError):
        shared.localize_time(pred)
    # Mean sea level
    msl = PLACES[place]['mean sea lvl']
    return SimpleNamespace(
        fvcom_ssh=fvcom_ssh,
        nemo_ssh=nemo_ssh,
        obs=obs,
        pred=pred,
        msl=msl,
    )


def _get_nemo_ssh(place, dataset_url_tmpl):
    ## TODO: This is a work-around because neither netCDF4 nor xarray are able
    ## to load the dataset directly from the URL due to an OpenDAP issue
    dataset_url = dataset_url_tmpl.format(place=place.replace(" ", ""))
    dataset_id = dataset_url.rsplit('/', 1)[1]
    ssh_file = Path('/tmp').joinpath(dataset_id).with_suffix('.nc')
    with ssh_file.open('wb') as f:
        resp = requests.get(f'{dataset_url}.nc')
        f.write(resp.content)
    try:
        nemo_ssh = xarray.open_dataset(ssh_file)
    except OSError:
        raise ValueError(f'NEMO ssh dataset not found for {place}')
    return nemo_ssh


def _prep_fig_axes(figsize, theme):
    fig, ax = plt.subplots(
        1, 1, figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor']
    )
    fig.autofmt_xdate()
    return fig, ax


def _plot_water_level_time_series(ax, place, plot_data, theme):
    with suppress(AttributeError):
        # CHS sometimes returns an empty prediction dataset
        if plot_data.pred.water_level.size:
            plot_data.pred.water_level.plot(
                ax=ax,
                linewidth=2,
                label='CHS Predicted',
                color=theme.COLOURS['time series']['tidal prediction']
            )
    with suppress(AttributeError):
        # CHS sometimes returns an empty observations dataset
        if plot_data.obs.water_level.size:
            plot_data.obs.water_level.plot(
                ax=ax,
                linewidth=2,
                label='CHS Observed',
                color=theme.COLOURS['time series']['tide gauge obs']
            )
    with suppress(AttributeError):
        (plot_data.nemo_ssh.ssh + plot_data.msl).plot(
            ax=ax,
            linewidth=2,
            label='NEMO',
            color=theme.COLOURS['time series']['tide gauge ssh']
        )
    (plot_data.fvcom_ssh + plot_data.msl).plot(
        ax=ax,
        linewidth=2,
        label='FVCOM',
        color=theme.COLOURS['time series']['vhfr fvcom ssh']
    )
    legend = ax.legend(prop=theme.FONTS['legend label small'])
    legend.set_title('Legend', prop=theme.FONTS['legend title small'])
    _water_level_time_series_labels(ax, place, plot_data, theme)


def _water_level_time_series_labels(ax, place, plot_data, theme):
    ax.set_title(
        f'Water Level at {place}',
        fontproperties=theme.FONTS['axes title'],
        color=theme.COLOURS['text']['axes title']
    )
    ax.set_xlabel(
        f'Time [{plot_data.fvcom_ssh.attrs["tz_name"]}]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d%b %H:%M'))
    ax.set_ylabel(
        'Water Level above Chart Datum [m]',
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis']
    )
    ax.grid(axis='both')
    theme.set_axis_colors(ax)