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

"""Produce a figure that shows colour contours of a tracer on a vertical slice 
along a section of the domain thalweg,
and on the surface for a section of the domain that excludes Puget Sound 
in the south and Johnstone Strait in the north.
"""
from types import SimpleNamespace

import matplotlib.pyplot as plt
from matplotlib import gridspec
import numpy as np

from salishsea_tools import visualisations as vis
from salishsea_tools import viz_tools

import nowcast.figures.shared
import nowcast.figures.website_theme


def make_figure(
    tracer_var, bathy, lons, lats, mesh_mask, coastline, cmap,
    depth_integrated, figsize=(20, 12),
    theme=nowcast.figures.website_theme
):
    """Plot colour contours of tracer on a vertical slice along a section of 
    the domain thalweg,
    and on the surface for the Strait of Georgia and Juan de Fuca Strait
    regions of the domain.
    
    :param tracer_var: Hourly average tracer results from NEMO run. 
    :type tracer_var: :py:class:`netCDF4.Variable`
    
    :param bathy: Salish Sea NEMO model bathymetry data.
    :type bathy: :py:class:`numpy.ndarray`

    :param lons: Salish Sea NEMO model longitude grid data.
    :type lons: :py:class:`numpy.ndarray`

    :param lats: Salish Sea NEMO model latitude grid data.
    :type lats: :py:class:`numpy.ndarray`

    :param mesh_mask: NEMO-generated mesh mask for run that produced tracer_var.
    :type mesh_mask: :class:`netCDF4.Dataset`
    
    :param coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`
    
    :param cmap: Colour map to use for tracer_var contour plots.
    :type cmap: :py:class:`matplotlib.colors.LinearSegmentedColormap`
    
    :param boolean depth_integrated: Integrate the tracer over the water column
                                     depth when :py:obj:`True`.
    
    :param 2-tuple figsize: Figure size (width, height) in inches.

    :param theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(tracer_var, mesh_mask, depth_integrated)
    fig, (ax_thalweg, ax_surface) = _prep_fig_axes(figsize, theme)

    clevels_thalweg, clevels_surface, show_thalweg_cbar = _calc_clevels(
        plot_data)

    cbar_thalweg = _plot_tracer_thalweg(
        ax_thalweg, plot_data, bathy, lons, lats, mesh_mask, cmap,
        clevels_thalweg)
    _thalweg_axes_labels(
        ax_thalweg, tracer_var, show_thalweg_cbar, clevels_thalweg,
        cbar_thalweg, theme)

    cbar_surface = _plot_tracer_surface(
        ax_surface, plot_data, cmap, clevels_surface)
    _surface_axes_labels(
        ax_surface, tracer_var, depth_integrated, clevels_surface, cbar_surface,
        theme)
    return fig


def _prep_plot_data(tracer_var, mesh_mask, depth_integrated):
    hr = 19
    sj, ej = 200, 770
    si, ei = 20, 370
    tracer_hr = tracer_var[hr]
    if depth_integrated:
        grid_heights = mesh_mask.variables['e3t_0'][:][0].reshape(
            tracer_hr.shape[0], 1, 1)
        height_weighted = tracer_hr[:, sj:ej, si:ei] * grid_heights
        surface_hr = height_weighted.sum(axis=0)
    else:
        surface_hr = tracer_hr[0, sj:ej, si:ei]
    surface_hr = np.ma.masked_where(
        mesh_mask["tmask"][0, 0, sj:ej, si:ei] == 0, surface_hr)

    return SimpleNamespace(
        tracer_hr=tracer_hr,
        surface_hr=surface_hr,
    )


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])

    gs = gridspec.GridSpec(1, 2, width_ratios=[1.3, 1])

    ax_thalweg = fig.add_subplot(gs[0])
    ax_thalweg.set_axis_bgcolor(theme.COLOURS['axes']['background'])

    ax_surface = fig.add_subplot(gs[1])
    ax_surface.set_axis_bgcolor(theme.COLOURS['axes']['background'])

    return fig, (ax_thalweg, ax_surface)


def _calc_clevels(plot_data):
    """Calculates contour levels for the two axes and decides whether whether
    the levels are similar enough that one colour bar is sufficient for the 
    figure, or if each axes requires one.
    """
    percent_98_surf = np.percentile(plot_data.surface_hr, 98)
    percent_2_surf = np.percentile(plot_data.surface_hr, 2)

    percent_98_grid = np.percentile(
        np.ma.masked_values(plot_data.tracer_hr, 0), 98)
    percent_2_grid = np.percentile(
        np.ma.masked_values(plot_data.tracer_hr, 0), 2)

    overlap = (
        max(0, min(percent_98_surf, percent_98_grid)
            - max(percent_2_surf, percent_2_grid)))
    magnitude = (
        (percent_98_surf - percent_2_surf) + (percent_98_grid - percent_2_grid))
    if 2 * overlap / magnitude > 0.5:
        max_clevel = max(percent_98_surf, percent_98_grid)
        min_clevel = min(percent_2_surf, percent_2_grid)
        clevels_thalweg = np.arange(
            min_clevel, max_clevel, (max_clevel - min_clevel) / 20.0)
        clevels_surface = clevels_thalweg
        show_thalweg_cbar = False
    else:
        clevels_thalweg = np.arange(
            percent_2_grid, percent_98_grid,
            (percent_98_grid - percent_2_grid) / 20.0)
        clevels_surface = np.arange(
            percent_2_surf, percent_98_surf,
            (percent_98_surf - percent_2_surf) / 20.0)
        show_thalweg_cbar = True
    return clevels_thalweg, clevels_surface, show_thalweg_cbar


def _plot_tracer_thalweg(
    ax, plot_data, bathy, lons, lats, mesh_mask, cmap, clevels
):
    cbar = vis.contour_thalweg(
        ax, plot_data.tracer_hr, bathy, lons, lats, mesh_mask,
        'gdept', clevels=clevels, cmap=cmap,
        thalweg_file='/results/nowcast-sys/tools/bathymetry/thalweg_working'
                     '.txt',
        cbar_args={'fraction': 0.030, 'pad': 0.04, 'aspect': 45}
    )
    return cbar


def _thalweg_axes_labels(
    ax, tracer_var, show_thalweg_cbar, clevels, cbar, theme
):
    ax.set_xlim(0, 590)
    ax.set_ylim(450, 0)
    if show_thalweg_cbar:
        label = f'{tracer_var.long_name} [{tracer_var.units}]'
        _cbar_labels(cbar, clevels[::2], theme, label)
    else:
        cbar.remove()
    ax.set_xlabel(
        'Distance along thalweg [km]', color=theme.COLOURS['text']['axis'],
        fontproperties=theme.FONTS['axis'])
    ax.set_ylabel(
        'Depth [m]', color=theme.COLOURS['text']['axis'],
        fontproperties=theme.FONTS['axis'])
    theme.set_axis_colors(ax)


def _cbar_labels(cbar, contour_intervals, theme, label):
    cbar.set_ticks(contour_intervals)
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
    cbar.set_label(
        label,
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis'])


def _plot_tracer_surface(ax, plot_data, cmap, clevels):
    x, y = np.meshgrid(
        np.arange(20, 370, dtype=int), np.arange(200, 770, dtype=int))
    mesh = ax.contourf(
        x, y, plot_data.surface_hr, levels=clevels, cmap=cmap, extend='both')
    cbar = plt.colorbar(mesh, ax=ax, fraction=0.034, pad=0.04, aspect=45)
    return cbar


def _surface_axes_labels(
    ax, tracer_var, depth_integrated, clevels, cbar, theme
):
    cbar_units = (
        f'{tracer_var.units}*m' if depth_integrated
        else f'{tracer_var.units}')
    cbar_label = f'{tracer_var.long_name} [{cbar_units}]'
    _cbar_labels(cbar, clevels[::2], theme, cbar_label)
    ax.set_xlabel(
        'Grid x', color=theme.COLOURS['text']['axis'],
        fontproperties=theme.FONTS['axis'])
    ax.set_ylabel(
        'Grid y', color=theme.COLOURS['text']['axis'],
        fontproperties=theme.FONTS['axis'])
    ax.set_axis_bgcolor('burlywood')
    viz_tools.set_aspect(ax)
    theme.set_axis_colors(ax)
