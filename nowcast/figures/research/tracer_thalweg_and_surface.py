#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
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
"""Produce a figure that shows colour contours of a tracer on a vertical slice
along a section of the domain thalweg,
and on the surface for a section of the domain that excludes Puget Sound
in the south and Johnstone Strait in the north.

.. note::
    This module us no longer used in production but it preserved here
    because the `figure development and testing docs`_ and notebooks
    refer to it.

.. _figure development and testing docs: https://salishsea-nowcast.readthedocs.io/en/latest/figures/create_fig_module.html#creating-a-figure-module


Testing notebook for this module is
https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/TestTracerThalwegAndSurface.ipynb

Development notebook for this module is
https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/research/DevelopTracerThalwegAndSurfaceModule.ipynb

"""
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec
from salishsea_tools import visualisations as vis
from salishsea_tools import viz_tools

import nowcast.figures.website_theme


def make_figure(
    tracer_var,
    bathy,
    mesh_mask,
    cmap,
    depth_integrated,
    figsize=(16, 9),
    theme=nowcast.figures.website_theme,
):
    """Plot colour contours of tracer on a vertical slice along a section of
    the domain thalweg,
    and on the surface for the Strait of Georgia and Juan de Fuca Strait
    regions of the domain.

    :param tracer_var: Hourly average tracer results from NEMO run.
    :type tracer_var: :py:class:`netCDF4.Variable`

    :param bathy: Salish Sea NEMO model bathymetry data.
    :type bathy: :class:`netCDF4.Dataset`

    :param mesh_mask: NEMO-generated mesh mask for run that produced tracer_var.
    :type mesh_mask: :class:`netCDF4.Dataset`

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

    clevels_thalweg, clevels_surface, show_thalweg_cbar = _calc_clevels(plot_data)

    cbar_thalweg = _plot_tracer_thalweg(
        ax_thalweg, plot_data, bathy, mesh_mask, cmap, clevels_thalweg
    )
    _thalweg_axes_labels(
        ax_thalweg, plot_data, show_thalweg_cbar, clevels_thalweg, cbar_thalweg, theme
    )

    cbar_surface = _plot_tracer_surface(ax_surface, plot_data, cmap, clevels_surface)
    _surface_axes_labels(
        ax_surface, tracer_var, depth_integrated, clevels_surface, cbar_surface, theme
    )
    return fig


def _prep_plot_data(tracer_var, mesh_mask, depth_integrated):
    hr = 19
    sj, ej = 200, 800
    si, ei = 20, 395

    tracer_hr = tracer_var[hr]
    masked_tracer_hr = np.ma.masked_where(mesh_mask["tmask"][0, ...] == 0, tracer_hr)
    surface_hr = masked_tracer_hr[0, sj:ej, si:ei]

    if depth_integrated:
        grid_heights = mesh_mask.variables["e3t_1d"][:][0].reshape(
            tracer_hr.shape[0], 1, 1
        )
        height_weighted = masked_tracer_hr[:, sj:ej, si:ei] * grid_heights
        surface_hr = height_weighted.sum(axis=0)

    return SimpleNamespace(
        tracer_var=tracer_var,
        tracer_hr=tracer_hr,
        surface_hr=surface_hr,
        surface_j_limits=(sj, ej),
        surface_i_limits=(si, ei),
        thalweg_depth_limits=(0, 450),
        thalweg_length_limits=(0, 632),
    )


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"])

    gs = gridspec.GridSpec(1, 2, width_ratios=[1.618, 1])

    ax_thalweg = fig.add_subplot(gs[0])
    ax_thalweg.set_facecolor(theme.COLOURS["axes"]["background"])

    ax_surface = fig.add_subplot(gs[1])
    ax_surface.set_facecolor(theme.COLOURS["axes"]["background"])

    return fig, (ax_thalweg, ax_surface)


def _calc_clevels(plot_data):
    """Calculates contour levels for the two axes and decides whether whether
    the levels are similar enough that one colour bar is sufficient for the
    figure, or if each axes requires one.
    """
    percent_98_surf = np.percentile(plot_data.surface_hr.compressed(), 98)
    percent_2_surf = np.percentile(plot_data.surface_hr.compressed(), 2)

    percent_98_grid = np.percentile(
        np.ma.masked_values(plot_data.tracer_hr, 0).compressed(), 98
    )
    percent_2_grid = np.percentile(
        np.ma.masked_values(plot_data.tracer_hr, 0).compressed(), 2
    )

    overlap = max(
        0, min(percent_98_surf, percent_98_grid) - max(percent_2_surf, percent_2_grid)
    )
    magnitude = (percent_98_surf - percent_2_surf) + (percent_98_grid - percent_2_grid)
    if 2 * overlap / magnitude > 0.5:
        max_clevel = max(percent_98_surf, percent_98_grid)
        min_clevel = min(percent_2_surf, percent_2_grid)
        clevels_thalweg = np.arange(
            min_clevel, max_clevel, (max_clevel - min_clevel) / 20.0
        )
        clevels_surface = clevels_thalweg
        show_thalweg_cbar = False
    else:
        clevels_thalweg = np.arange(
            percent_2_grid, percent_98_grid, (percent_98_grid - percent_2_grid) / 20.0
        )
        clevels_surface = np.arange(
            percent_2_surf, percent_98_surf, (percent_98_surf - percent_2_surf) / 20.0
        )
        show_thalweg_cbar = True
    return clevels_thalweg, clevels_surface, show_thalweg_cbar


def _plot_tracer_thalweg(ax, plot_data, bathy, mesh_mask, cmap, clevels):
    cbar = vis.contour_thalweg(
        ax,
        plot_data.tracer_hr,
        bathy,
        mesh_mask,
        clevels=clevels,
        cmap=cmap,
        ## TODO: Can this path be moved into nowcast.yaml config file?
        thalweg_file="/SalishSeaCast/tools/bathymetry/thalweg_working" ".txt",
        cbar_args={"fraction": 0.030, "pad": 0.04, "aspect": 45},
    )
    return cbar


def _thalweg_axes_labels(ax, plot_data, show_thalweg_cbar, clevels, cbar, theme):
    ax.set_xlim(plot_data.thalweg_length_limits)
    ax.set_ylim(plot_data.thalweg_depth_limits[1], plot_data.thalweg_depth_limits[0])
    if show_thalweg_cbar:
        label = f"{plot_data.tracer_var.long_name} [{plot_data.tracer_var.units}]"
        _cbar_labels(cbar, clevels[::2], theme, label)
    else:
        cbar.remove()
    ax.set_xlabel(
        "Distance along thalweg [km]",
        color=theme.COLOURS["text"]["axis"],
        fontproperties=theme.FONTS["axis"],
    )
    ax.set_ylabel(
        "Depth [m]",
        color=theme.COLOURS["text"]["axis"],
        fontproperties=theme.FONTS["axis"],
    )
    theme.set_axis_colors(ax)


def _cbar_labels(cbar, contour_intervals, theme, label):
    cbar.set_ticks(contour_intervals)
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS["cbar"]["tick labels"])
    cbar.set_label(
        label, fontproperties=theme.FONTS["axis"], color=theme.COLOURS["text"]["axis"]
    )


def _plot_tracer_surface(ax, plot_data, cmap, clevels):
    x, y = np.meshgrid(
        np.arange(*plot_data.surface_i_limits, dtype=int),
        np.arange(*plot_data.surface_j_limits, dtype=int),
    )
    mesh = ax.contourf(
        x, y, plot_data.surface_hr, levels=clevels, cmap=cmap, extend="both"
    )
    cbar = plt.colorbar(mesh, ax=ax, fraction=0.034, pad=0.04, aspect=45)
    return cbar


def _surface_axes_labels(ax, tracer_var, depth_integrated, clevels, cbar, theme):
    cbar_units = f"{tracer_var.units}*m" if depth_integrated else f"{tracer_var.units}"
    cbar_label = f"{tracer_var.long_name} [{cbar_units}]"
    _cbar_labels(cbar, clevels[::2], theme, cbar_label)
    ax.set_xlabel(
        "Grid x",
        color=theme.COLOURS["text"]["axis"],
        fontproperties=theme.FONTS["axis"],
    )
    ax.set_ylabel(
        "Grid y",
        color=theme.COLOURS["text"]["axis"],
        fontproperties=theme.FONTS["axis"],
    )
    ax.set_facecolor("burlywood")
    viz_tools.set_aspect(ax)
    theme.set_axis_colors(ax)
