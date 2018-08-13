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
"""Produce a 4-panel figure that shows surface values of temperature, salinity,
diatoms biomass, and nitrate concentration in the Baynes Sound region at 12:30
Pacific time. Each panel shows all of the Baynes Sound sub-grid as well as
a fringe of the full domain on the 3 non-land sides. The axes grid and tick
labels are an angled lon/lat grid.

Testing notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/research/TestBaynesSoundAGRIF.ipynb

Development notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/research/DevelopBaynesSoundAGRIF.ipynb
"""
from types import SimpleNamespace

import cmocean
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy
import xarray

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    ss_phys_url,
    bs_phys_path,
    ss_bio_url,
    bs_bio_path,
    run_date,
    ss_grid_url,
    bs_grid_path,
    figsize=(22, 9),
    theme=nowcast.figures.website_theme
):
    """Plot 4-panel figure that shows surface values of temperature, salinity,
    diatoms biomass, and nitrate concentration in the Baynes Sound region at
    12:30 Pacific time. Each panel shows all of the Baynes Sound sub-grid
    as well as a fringe of the full domain on the 3 non-land sides. The axes
    grid and tick labels are an angled lon/lat grid.

    :param str ss_phys_url: ERDDAP URL for the full domain hourly physics
                            tracers dataset.

    :param bs_phys_path: File path of Baynes Sound sub-grid hourly physics
                         tracers dataset.
    :type bs_phys_path: :py:class:`pathlib.Path`

    :param str ss_bio_url: ERDDAP URL for the full domain hourly biology
                           tracers dataset.

    :param bs_bio_path: File path of Baynes Sound sub-grid hourly biology
                        tracers dataset.
    :type bs_bio_path: :py:class:`pathlib.Path`

    :param run_date: Run date to produce the figure for.
    :type :py:class:`arrow.Arrow` run_date:

    :param str ss_grid_url: ERDDAP URL for the full domain geo-location and
                            bathymetry dataset that provides longitudes and
                            latitudes of the domain grid, and water depths.

    :param bs_grid_path: File path of Baynes Sound sub-grid bathymetry dataset
                         that provides longitudes and latitudes of the
                         sub-grid, and water depths.
    :type :py:class:`pathlib.Path` bs_grid_path:

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(
        ss_phys_url, bs_phys_path, ss_bio_url, bs_bio_path, run_date,
        ss_grid_url, bs_grid_path
    )
    fig, axs, grids = _prep_fig_axes(figsize, plot_data, theme)
    _plot_surface_fields(axs, plot_data, grids, theme)

    time = plot_data.bs_temperature.time_counter
    year = numpy.asscalar(time.dt.year.values)
    month = numpy.asscalar(time.dt.month.values)
    day = numpy.asscalar(time.dt.day.values)
    hour = numpy.asscalar(time.dt.hour.values)
    minute = numpy.asscalar(time.dt.minute.values)
    fig.suptitle(
        f'{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d} {plot_data.tz_name}',
        color=theme.COLOURS['text']['figure title'],
        fontproperties=theme.FONTS['figure title'],
        fontsize=theme.FONTS['figure title'].get_size(),
    )
    return fig


def _prep_plot_data(
    ss_phys_url, bs_phys_path, ss_bio_url, bs_bio_path, run_date, ss_grid_url,
    bs_grid_path
):
    """
    :param str ss_phys_url:
    :param :py:class:`pathlib.Path` bs_phys_path:
    :param str ss_bio_url:
    :param :py:class:`pathlib.Path` bs_bio_path:
    :param :py:class:`arrow.Arrow` run_date:
    :param str ss_grid_url:
    :param :py:class:`pathlib.Path` bs_grid_path:
    :returns: :py:class:`types.SimpleNamespace`
    """

    ss_phys = xarray.open_dataset(ss_phys_url)
    ss_bio = xarray.open_dataset(ss_bio_url)
    for dataset in (ss_phys, ss_bio):
        shared.localize_time(dataset, time_coord='time')

    bs_phys = xarray.open_dataset(bs_phys_path)
    bs_bio = xarray.open_dataset(bs_bio_path)
    for dataset in (bs_phys, bs_bio):
        shared.localize_time(dataset, time_coord='time_counter')

    ss_grid = xarray.open_dataset(ss_grid_url, mask_and_scale=False)
    ss_water_mask = ss_grid.bathymetry != 0
    bs_grid = xarray.open_dataset(bs_grid_path, mask_and_scale=False)
    bs_water_mask = bs_grid.Bathymetry != 0

    ss_temperature = _get_data_array(
        ss_phys.temperature, ss_water_mask, run_date
    )
    bs_temperature = _get_data_array(bs_phys.votemper, bs_water_mask, run_date)
    bs_temperature.attrs['long_name'] = 'Conservative Temperature'
    ss_salinity = _get_data_array(ss_phys.salinity, ss_water_mask, run_date)
    bs_salinity = _get_data_array(bs_phys.vosaline, bs_water_mask, run_date)
    bs_salinity.attrs['long_name'] = 'Reference Salinity'
    ss_diatoms = _get_data_array(ss_bio.diatoms, ss_water_mask, run_date)
    bs_diatoms = _get_data_array(bs_bio.diatoms, bs_water_mask, run_date)
    ss_nitrate = _get_data_array(ss_bio.nitrate, ss_water_mask, run_date)
    bs_nitrate = _get_data_array(bs_bio.nitrate, bs_water_mask, run_date)
    return SimpleNamespace(
        ss_temperature=ss_temperature,
        bs_temperature=bs_temperature,
        ss_salinity=ss_salinity,
        bs_salinity=bs_salinity,
        ss_diatoms=ss_diatoms,
        bs_diatoms=bs_diatoms,
        ss_nitrate=ss_nitrate,
        bs_nitrate=bs_nitrate,
        run_date=run_date,
        tz_name=bs_phys.attrs['tz_name'],
        ss_grid=ss_grid,
        bs_grid=bs_grid,
    )


def _get_data_array(ds_var, water_mask, run_date):
    """
    :param :py:class:`xarray.DataArray` ds_var:
    :param :py:class:`xarray.DataArray` water_mask:
    :param :py:class:`arrow.Arrow` run_date:
    :returns: :py:class:`xarray.DataArray`
    """
    try:
        return ds_var \
            .isel(deptht=0) \
            .sel(time_counter=run_date.format('YYYY-MM-DD 12:30')) \
            .where(water_mask)
    except ValueError:
        return ds_var \
            .isel(depth=0) \
            .sel(time=run_date.format('YYYY-MM-DD 12:30')) \
            .where(water_mask)


def _prep_fig_axes(figsize, plot_data, theme):
    """
    :param 2-tuple figsize:
    :param :py:class:`types.SimpleNamespace` plot_data:
    :param :py:mod:`nowcast.figures.website_theme` theme:
    :returns: :py:class:`matplotlib.figure.Figure`,
              4-tuple of :py:class:`matplotlib.axes.Axes`,
              `types.SimpleNamespace`
    """
    fig, axs = plt.subplots(
        1, 4, figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor']
    )
    map_params = SimpleNamespace(
        ll_lon=-124.68,
        ur_lon=-124.86,
        ll_lat=49.25,
        ur_lat=49.925,
        lon_0_offset=37.9,
        meridians=numpy.arange(-125.1, -124.3, 0.1),
        parallels=numpy.arange(49.2, 50, 0.1),
    )
    central_lon = ((map_params.ur_lon - map_params.ll_lon) / 2 +
                   map_params.ll_lon + map_params.lon_0_offset)
    central_lat = ((map_params.ur_lat - map_params.ll_lat) / 2 +
                   map_params.ll_lat)
    for ax in axs:
        m = Basemap(
            ax=ax,
            projection='lcc',
            lon_0=central_lon,
            lat_0=central_lat,
            llcrnrlon=map_params.ll_lon,
            urcrnrlon=map_params.ur_lon,
            llcrnrlat=map_params.ll_lat,
            urcrnrlat=map_params.ur_lat,
        )
        # lon/lat grid
        m.drawmeridians(
            map_params.meridians,
            labels=(False, False, False, True),
            textcolor=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis small'],
        )
        m.drawparallels(
            map_params.parallels,
            labels=(True, False, False, False),
            textcolor=theme.COLOURS['text']['axis'],
            fontproperties=theme.FONTS['axis small'],
        )
    ss_x, ss_y = m(
        plot_data.ss_grid.longitude.values, plot_data.ss_grid.latitude.values
    )
    bs_x, bs_y = m(
        plot_data.bs_grid.nav_lon.values, plot_data.bs_grid.nav_lat.values
    )
    grids = SimpleNamespace(ss_x=ss_x, ss_y=ss_y, bs_x=bs_x, bs_y=bs_y)
    return fig, axs, grids


def _plot_surface_fields(axs, plot_data, grids, theme):
    """
    :param 4-tuple of :py:class:`matplotlib.axes.Axes` axs:
    :param :py:class:`types.SimpleNamespace` plot_data:
    :param `types.SimpleNamespace` grids:
    :param :py:mod:`nowcast.figures.website_theme` theme:
    """
    vars = [
        (
            plot_data.ss_temperature, plot_data.bs_temperature,
            cmocean.cm.thermal
        ),
        (plot_data.ss_salinity, plot_data.bs_salinity, cmocean.cm.haline),
        (plot_data.ss_diatoms, plot_data.bs_diatoms, cmocean.cm.algae),
        (plot_data.ss_nitrate, plot_data.bs_nitrate, cmocean.cm.matter),
    ]
    for i, (ss_var, bs_var, cmap) in enumerate(vars):
        _plot_surface_field(
            axs[i], ss_var, bs_var, cmap, grids, plot_data.bs_grid.Bathymetry,
            theme
        )


def _plot_surface_field(ax, ss_var, bs_var, cmap, grids, bs_bathy, theme):
    """
    :param :py:class:`matplotlib.axes.Axes` ax:
    :param :py:class:`xarray.DataArray` ss_var:
    :param :py:class:`xarray.DataArray` bs_var:
    :param :py:class:`matplotlib.colors.ListedColormap` cmap:
    :param `types.SimpleNamespace` grids:
    :param :py:class:`xarray.DataArray` bs_bathy:
    :param :py:mod:`nowcast.figures.website_theme` theme:
    """
    cmap = plt.get_cmap(cmap)
    clevels = numpy.linspace(
        numpy.floor(bs_var.where(bs_var > 0).min()),
        numpy.ceil(bs_var.where(bs_var > 0).max()), 20
    )
    ax.contourf(
        grids.ss_x,
        grids.ss_y,
        ss_var,
        cmap=cmap,
        levels=clevels,
        extend='max'
    )
    contour_set = ax.contourf(
        grids.bs_x,
        grids.bs_y,
        bs_var,
        cmap=cmap,
        levels=clevels,
        extend='max'
    )
    ax.set_axis_bgcolor('burlywood')
    cbar = plt.colorbar(contour_set, ax=ax)
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
    cbar.set_label(
        f'{bs_var.attrs["long_name"]} [{bs_var.attrs["units"]}]',
        color=theme.COLOURS['text']['axis'],
        fontproperties=theme.FONTS['axis'],
    )
    isobath = ax.contour(
        grids.bs_x,
        grids.bs_y,
        bs_bathy,
        (25,),
        colors=theme.COLOURS['contour lines']['Baynes Sound entrance'],
    )
    plt.clabel(isobath, fmt={isobath.levels[0]: f'{isobath.levels[0]:.0f} m'})
    theme.set_axis_colors(ax)
