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
    tracer_grid, bathy, lons, lats, mesh_mask, coastline, cmap,
    depth_integrated=True, figsize=(20, 12),
    theme=nowcast.figures.website_theme
):
    """Plot colour contours of tracer on a vertical slice along a section of 
    the domain thalweg,
    and on the surface for the Strait of Georgia and Juan de Fuca Strait
    regions of the domain.
    
    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(
        tracer_grid, bathy, lons, lats, mesh_mask, coastline, depth_integrated
    )
    fig, (ax_thalweg, ax_surface) = _prep_fig_axes(figsize, theme)
    _plot_thalweg(ax_thalweg, plot_data, cmap, theme)
    _plot_surface(ax_surface, plot_data, cmap, theme)
    return fig


def _prep_plot_data(
    tracer_grid, bathy, lons, lats, mesh_mask, coastline, depth_integrated
):
    lon_range = (-124.4, -122.4)
    lat_range = (48, 51)
    si, ei = 150, 610
    sj, ej = 20, 370

    lons_subset = lons[si:ei, sj:ej]
    lats_subset = lats[si:ei, sj:ej]
    if depth_integrated:
        grid_heights = mesh_mask.variables['e3t_0'][:][0].reshape(40, 1, 1)
        height_weighted = tracer_grid[0, :, si:ei, sj:ej] * grid_heights
        surface_var = height_weighted.sum(axis=0)
    else:
        surface_var = tracer_grid[0, 0, si:ei, sj:ej]
    surface_var = np.ma.masked_array(
        surface_var, 1 - mesh_mask['tmask'][0, 0, si:ei, sj:ej])

    thal_clevels, surf_clevels, show_thalweg_cbar = surf_thalweg_clevels(
        tracer_grid, surface_var)

    if 'standard_name' in tracer_grid.ncattrs():
        tracer_name = tracer_grid.standard_name
    elif 'long_name' in tracer_grid.ncattrs():
        tracer_name = tracer_grid.long_name
    else:
        tracer_name = "Var"

    return SimpleNamespace(
        tracer_grid=tracer_grid[0, ...],
        var_ma=surface_var,
        bathy=bathy,
        lons=lons,
        lats=lats,
        lons_subset=lons_subset,
        lats_subset=lats_subset,
        mesh_mask=mesh_mask,
        coastline=coastline,
        lon_range=lon_range,
        lat_range=lat_range,
        thal_clevels=thal_clevels,
        surf_clevels=surf_clevels,
        show_thalweg_cbar=show_thalweg_cbar,
        tracer_name=tracer_name,
        units=tracer_grid.units,
        depth_integrated=depth_integrated,
    )


def surf_thalweg_clevels(tracer_grid, surface_var):
    percent_98_surf = np.percentile(surface_var, 98)
    percent_2_surf = np.percentile(surface_var, 2)

    percent_98_grid = np.percentile(np.ma.masked_values(tracer_grid, 0), 98)
    percent_2_grid = np.percentile(np.ma.masked_values(tracer_grid, 0), 2)

    overlap = (
        max(0, min(percent_98_surf, percent_98_grid)
            - max(percent_2_surf, percent_2_grid)))
    magnitude = (
        (percent_98_surf - percent_2_surf)
        + (percent_98_grid - percent_2_grid))
    if 2 * overlap / magnitude > 0.5:
        max_clevel = max(percent_98_surf, percent_98_grid)
        min_clevel = min(percent_2_surf, percent_2_grid)
        thal_clevels = np.arange(min_clevel, max_clevel,
                                 (max_clevel - min_clevel) / 20.0)
        surf_clevels = thal_clevels
        show_thalweg_cbar = False
    else:
        thal_clevels = np.arange(percent_2_grid, percent_98_grid,
                                 (percent_98_grid - percent_2_grid) / 20.0)
        surf_clevels = np.arange(percent_2_surf, percent_98_surf,
                                 (percent_98_surf - percent_2_surf) / 20.0)
        show_thalweg_cbar = True
    return thal_clevels, surf_clevels, show_thalweg_cbar


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])

    gs = gridspec.GridSpec(1, 2, width_ratios=[1.14, 1])

    ax_thalweg = fig.add_subplot(gs[0])
    ax_thalweg.set_axis_bgcolor(theme.COLOURS['axes']['background'])

    ax_surface = fig.add_subplot(gs[1])
    ax_surface.set_axis_bgcolor(theme.COLOURS['axes']['background'])

    return fig, (ax_thalweg, ax_surface)


def _plot_thalweg(ax, plot_data, cmap, theme):
    cbar = vis.contour_thalweg(
        ax, plot_data.tracer_grid, plot_data.bathy, plot_data.lons,
        plot_data.lats, plot_data.mesh_mask,
        'gdept', clevels=plot_data.thal_clevels, cmap=cmap,
        thalweg_file='/results/nowcast-sys/tools/bathymetry/thalweg_working.txt',
        cbar_args={'fraction': 0.030, 'pad': 0.04})
    viz_tools.set_aspect(ax)
    ax.set_ylim([450, 0])
    if not plot_data.show_thalweg_cbar:
        cbar.remove()
    else:
        contour_intervals = plot_data.thal_clevels
        label = plot_data.tracer_name + " [" + plot_data.units + "]"
        _map_cbar_labels(cbar, contour_intervals[::2], theme, label)
    ax.set_xlabel("Distance along thalweg [km]",
                  color=theme.COLOURS['text']['axis'],
                  fontproperties=theme.FONTS['axis'])
    ax.set_ylabel("Depth [m]", color=theme.COLOURS['text']['axis'],
                  fontproperties=theme.FONTS['axis'])
    theme.set_axis_colors(ax)


def _map_cbar_labels(cbar, contour_intervals, theme, label):
    cbar.set_ticks(contour_intervals)
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS['cbar']['tick labels'])
    cbar.set_label(
        label,
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis'])


def _plot_surface(ax, plot_data, cmap, theme):
    nowcast.figures.shared.plot_map(ax, plot_data.coastline,
                                    lon_range=plot_data.lon_range,
                                    lat_range=plot_data.lat_range)
    mesh = ax.contourf(plot_data.lons_subset, plot_data.lats_subset,
                       plot_data.var_ma, levels=plot_data.surf_clevels,
                       cmap=cmap, extend='both')

    ax.set_xlabel('Longitude', color=theme.COLOURS['text']['axis'],
                  fontproperties=theme.FONTS['axis'])
    ax.set_ylabel('Latitude', color=theme.COLOURS['text']['axis'],
                  fontproperties=theme.FONTS['axis'])
    theme.set_axis_colors(ax)

    cbar = plt.colorbar(mesh, ax=ax, fraction=0.034, pad=0.04)
    contour_intervals = plot_data.surf_clevels
    if plot_data.depth_integrated:
        label = plot_data.tracer_name + " [" + plot_data.units + "*m]"
    else:
        label = plot_data.tracer_name + " [" + plot_data.units + "]"
    _map_cbar_labels(cbar, contour_intervals[::2], theme, label)
