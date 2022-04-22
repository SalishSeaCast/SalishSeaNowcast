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
"""Produce a 4-panel figure that shows surface values of temperature, salinity,
diatoms biomass, and nitrate concentration in the Baynes Sound region at 12:30
Pacific time. Each panel shows all of the Baynes Sound sub-grid as well as
a fringe of the full domain on the 3 non-land sides. The axes grid and tick
labels are an angled lon/lat grid.

Testing notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestBaynesSoundAGRIF.ipynb

Development notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopBaynesSoundAGRIF.ipynb
"""
from types import SimpleNamespace

import cartopy
import cmocean
import matplotlib.pyplot as plt
import numpy
import xarray

import nowcast.figures.website_theme
from nowcast.figures import shared


def make_figure(
    ss_tracers_path,
    bs_phys_path,
    bs_bio_path,
    run_date,
    ss_grid_url,
    bs_grid_path,
    figsize=(22, 9),
    theme=nowcast.figures.website_theme,
):
    """Plot 4-panel figure that shows surface values of temperature, salinity,
    diatoms biomass, and nitrate concentration in the Baynes Sound region at
    12:30 Pacific time. Each panel shows all of the Baynes Sound sub-grid
    as well as a fringe of the full domain on the 3 non-land sides. The axes
    grid and tick labels are an angled lon/lat grid.

    :param ss_tracers_path: File path of full domain hourly physics tracers
                            dataset.
    :type ss_tracers_path: :py:class:`pathlib.Path`

    :param bs_phys_path: File path of Baynes Sound sub-grid hourly physics
                         tracers dataset.
    :type bs_phys_path: :py:class:`pathlib.Path`

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

    :param 2-tuple figsize: Figure size (width, height) in inches.

    :param theme: Module-like object that defines the style elements for the
                  figure. See :py:mod:`nowcast.figures.website_theme` for an
                  example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(
        ss_tracers_path, bs_phys_path, bs_bio_path, run_date, ss_grid_url, bs_grid_path
    )
    fig, axs = _prep_fig_axes(figsize, plot_data, theme)
    _plot_surface_fields(axs, plot_data, theme)
    _axes_labels(axs, theme)

    time = plot_data.bs_temperature.time_counter
    year = time.dt.year.values.item()
    month = time.dt.month.values.item()
    day = time.dt.day.values.item()
    hour = time.dt.hour.values.item()
    minute = time.dt.minute.values.item()
    fig.suptitle(
        f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d} {plot_data.tz_name}",
        color=theme.COLOURS["text"]["figure title"],
        fontproperties=theme.FONTS["figure title"],
        fontsize=theme.FONTS["figure title"].get_size(),
    )
    fig.canvas.draw()
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    return fig


def _prep_plot_data(
    ss_tracers_path, bs_phys_path, bs_bio_path, run_date, ss_grid_url, bs_grid_path
):
    """
    :type ss_tracers_path: :py:class:`pathlib.Path`
    :type bs_phys_path: :py:class:`pathlib.Path`
    :type bs_bio_path: :py:class:`pathlib.Path`
    :type run_date: :py:class:`arrow.Arrow`
    :type ss_grid_url: str
    :type bs_grid_path: :py:class:`pathlib.Path`

    :rtype: :py:class:`types.SimpleNamespace`
    """
    SS_BAYNES_SOUND_X, SS_BAYNES_SOUND_Y = slice(112, 166), slice(550, 699)
    ss_grid = xarray.open_dataset(ss_grid_url, mask_and_scale=False).sel(
        gridX=SS_BAYNES_SOUND_X, gridY=SS_BAYNES_SOUND_Y
    )
    ss_water_mask = (ss_grid.bathymetry != 0).values
    bs_grid = xarray.open_dataset(bs_grid_path, mask_and_scale=False)
    bs_water_mask = (bs_grid.Bathymetry != 0).values

    ss_tracers = xarray.open_dataset(ss_tracers_path)
    shared.localize_time(ss_tracers, time_coord="time_counter")

    bs_phys = xarray.open_dataset(bs_phys_path)
    bs_bio = xarray.open_dataset(bs_bio_path)
    for dataset in (bs_phys, bs_bio):
        shared.localize_time(dataset, time_coord="time_counter")

    ss_temperature = _get_data_array(ss_tracers.votemper, ss_water_mask, run_date)
    bs_temperature = _get_data_array(bs_phys.votemper, bs_water_mask, run_date)
    bs_temperature.attrs["long_name"] = "Conservative Temperature"
    ss_salinity = _get_data_array(ss_tracers.vosaline, ss_water_mask, run_date)
    bs_salinity = _get_data_array(bs_phys.vosaline, bs_water_mask, run_date)
    bs_salinity.attrs["long_name"] = "Reference Salinity"
    ss_diatoms = _get_data_array(ss_tracers.diatoms, ss_water_mask, run_date)
    bs_diatoms = _get_data_array(bs_bio.diatoms, bs_water_mask, run_date)
    ss_nitrate = _get_data_array(ss_tracers.nitrate, ss_water_mask, run_date)
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
        tz_name=bs_phys.attrs["tz_name"],
        ss_grid=ss_grid,
        bs_grid=bs_grid,
    )


def _get_data_array(ds_var, water_mask, run_date):
    """
    :type ds_var: :py:class:`xarray.DataArray`
    :type water_mask: :py:class:`xarray.DataArray`
    :type run_date: :py:class:`arrow.Arrow`

    :rtype: :py:class:`xarray.DataArray`
    """
    try:
        return (
            ds_var.isel(nearsurface_T=0)
            .sel(time_counter=run_date.format("YYYY-MM-DD 12:30"))
            .where(water_mask)
        )
    except ValueError:
        return (
            ds_var.isel(deptht=0)
            .sel(time_counter=run_date.format("YYYY-MM-DD 12:30"))
            .where(water_mask)
        )


def _prep_fig_axes(figsize, plot_data, theme):
    """
    :type figsize: 2-tuple
    :type plot_data: :py:class:`types.SimpleNamespace`
    :type theme: :py:mod:`nowcast.figures.website_theme`

    :rtype: :py:class:`matplotlib.figure.Figure`,
            4-tuple of :py:class:`matplotlib.axes.Axes`
    """
    rotated_crs = cartopy.crs.RotatedPole(pole_longitude=120.0, pole_latitude=63.75)
    fig, axs = plt.subplots(
        1,
        4,
        figsize=figsize,
        facecolor=theme.COLOURS["figure"]["facecolor"],
        subplot_kw={"projection": rotated_crs, "facecolor": theme.COLOURS["dark land"]},
    )
    return fig, axs


def _plot_surface_fields(axs, plot_data, theme):
    """
    :type axs: 4-tuple of :py:class:`matplotlib.axes.Axes`
    :type plot_data: :py:class:`types.SimpleNamespace`
    :type theme: :py:mod:`nowcast.figures.website_theme`
    """
    vars = [
        (plot_data.ss_temperature, plot_data.bs_temperature, cmocean.cm.thermal),
        (plot_data.ss_salinity, plot_data.bs_salinity, cmocean.cm.haline),
        (plot_data.ss_diatoms, plot_data.bs_diatoms, cmocean.cm.algae),
        (plot_data.ss_nitrate, plot_data.bs_nitrate, cmocean.cm.matter),
    ]
    for i, (ss_var, bs_var, cmap) in enumerate(vars):
        _plot_surface_field(
            axs[i], ss_var, bs_var, cmap, plot_data.ss_grid, plot_data.bs_grid, theme
        )


def _plot_surface_field(ax, ss_var, bs_var, cmap, ss_grid, bs_grid, theme):
    """
    :type ax: :py:class:`matplotlib.axes.Axes`
    :type ss_var: :py:class:`xarray.DataArray`
    :type bs_var: :py:class:`xarray.DataArray`
    :type cmap: :py:class:`matplotlib.colors.ListedColormap`
    :type ss_grid: :py:class:`xarray.DataArray`
    :type bs_grid: :py:class:`xarray.DataArray`
    :type theme: :py:mod:`nowcast.figures.website_theme`
    """
    plain_crs = cartopy.crs.PlateCarree()
    clevels = numpy.linspace(
        numpy.floor(bs_var.where(bs_var > 0).min()),
        numpy.ceil(bs_var.where(bs_var > 0).max()),
        20,
    )
    ax.contourf(
        ss_grid.longitude,
        ss_grid.latitude,
        ss_var,
        transform=plain_crs,
        cmap=cmap,
        levels=clevels,
        extend="max",
    )
    map_extent = ax.get_extent()
    contour_set = ax.contourf(
        bs_grid.nav_lon,
        bs_grid.nav_lat,
        bs_var,
        transform=plain_crs,
        cmap=cmap,
        levels=clevels,
        extend="max",
    )
    ax.set_extent(map_extent, crs=ax.projection)
    cbar = plt.colorbar(contour_set, ax=ax)
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS["cbar"]["tick labels"])
    cbar.set_label(
        f'{bs_var.attrs["long_name"]} [{bs_var.attrs["units"]}]',
        color=theme.COLOURS["text"]["axis"],
        fontproperties=theme.FONTS["axis"],
    )
    isobath = ax.contour(
        bs_grid.nav_lon,
        bs_grid.nav_lat,
        bs_grid.Bathymetry,
        (25,),
        transform=plain_crs,
        colors=theme.COLOURS["contour lines"]["Baynes Sound entrance"],
    )
    ax.clabel(isobath, fmt={isobath.levels[0]: f"{isobath.levels[0]:.0f} m"})


def _axes_labels(axs, theme):
    """
    :type axs: 4-tuple of :py:class:`matplotlib.axes.Axes`
    :type theme: :py:mod:`nowcast.figures.website_theme`
    """
    for ax in axs:
        glines = ax.gridlines(draw_labels=True, auto_inline=False)
        glines.right_labels, glines.top_labels = False, False
        glines.xlabel_style = {
            "color": theme.COLOURS["text"]["axis"],
            "fontproperties": theme.FONTS["axis small"],
        }
        glines.ylabel_style = {
            "color": theme.COLOURS["text"]["axis"],
            "fontproperties": theme.FONTS["axis small"],
        }
