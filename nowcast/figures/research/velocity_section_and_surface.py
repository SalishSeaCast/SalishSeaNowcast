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
"""Produce a figure that shows colour contours of a tracer on a vertical slice
along a section of the domain thalweg,
and on the surface for a section of the domain that excludes Puget Sound 
in the south and Johnstone Strait in the north.
"""
from types import SimpleNamespace

import matplotlib.pyplot as plt
from matplotlib import gridspec
import numpy as np
import cmocean

from salishsea_tools import viz_tools

import nowcast.figures.website_theme


def make_figure(
    U_var,
    V_var,
    bathy,
    mesh_mask,
    cmap=cmocean.cm.curl,
    figsize=(20, 12),
    theme=nowcast.figures.website_theme,
    levels=np.arange(-0.55, 0.60, 0.05),
    ibreak=24,
    sections=(450,),
    pos=((0.1, 0.95),),
    section_lims=((235, 318, 0, 445),),
    surface_lims=(0, 397, 200, 750),
):
    """Produce a figure that shows colour contours of a tracer on a vertical slice 
    along a section of the domain thalweg,
    and on the surface for a section of the domain that excludes Puget Sound 
    in the south and Johnstone Strait in the north.

    :param U_var: Hourly average U velocity from NEMO run
    :type U_var: :class:`numpy.ndarray`

    :param V_var: Hourly average V velocity from NEMO run
    :type V_var: :class:`numpy.ndarray`

    :param bathy: Salish Sea NEMO model bathymetry data.
    :type bathy: :class:`netCDF4.Dataset`

    :param mesh_mask: NEMO-generated mesh mask for run that produced tracer_var.
    :type mesh_mask: :class:`netCDF4.Dataset`

    :param cmap: Colour map to use for tracer_var contour plots.
    :type cmap: :py:class:`matplotlib.colors.LinearSegmentedColormap`

    :param 2-tuple figsize: Figure size (width, height) in inches.

    :param theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :param levels: List of numbers indicating level curves to draw in increasing order.
    :type levels: :class:`numpy.ndarray`

    :param ibreak: 
    :type ibreak: `int`

    :param 1-tuple sections: tuple of section to plot velocity.

    :param 2-tuple pos: position of subfigures in their axis. 
  
    :param 4-tuple section_lims: 4-tuple of axis limits for section plots in form of (xmin, xmax, zmin, zmax)

    :param 4-tuple surface_lims: 4-tuple of axis limits for surface plot in form of (xmin, xmax, ymin, ymax)

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    # Prepare data
    plot_data = _prep_plot_data(U_var, V_var, mesh_mask, bathy, sections=sections)

    # Prepare layout
    fig, (ax_section, ax_surface, ax_cbar) = _prep_fig_axes(
        figsize, theme, sections=sections, pos=pos
    )

    # Plot sections
    for index, section in enumerate(zip(sections, section_lims)):
        if index == 0:
            xlabel = True
        else:
            xlabel = False
        cbar = _plot_vel_section(
            fig,
            ax_section[str(section[0])],
            ax_cbar,
            plot_data.V_section[index, ...],
            plot_data,
            plot_data.bathy_array[section[0], 1:],
            cmap=cmap,
            levels=levels,
            ibreak=ibreak,
        )
        _section_axes_labels(
            ax_section[str(section[0])],
            plot_data,
            theme,
            lims=section[1],
            ibreak=ibreak,
            xlabel=xlabel,
        )
    _cbar_labels(cbar, np.arange(-0.5, 0.6, 0.1), theme, "Alongstrait Velocity [m/s]")

    # Plot surface
    _plot_vel_surface(ax_surface, plot_data, bathy, sections=(sections, section_lims))
    _surface_axes_labels(ax_surface, theme, lims=surface_lims)

    return fig


def _prep_plot_data(U, V, mesh_mask, bathy, hr=0, sections=(450,)):

    # Index, mask, and unstagger U and V
    U_trim, V_trim = viz_tools.unstagger(
        np.ma.masked_where(mesh_mask["umask"][0, ...] == 0, U[hr, ...]),
        np.ma.masked_where(mesh_mask["vmask"][0, ...] == 0, V[hr, ...]),
    )

    # Extract surface
    U_surface = U_trim[0, ...]
    V_surface = V_trim[0, ...]

    # Extract sections
    dims = U_trim.shape
    U_section = np.zeros((len(sections), dims[0], dims[2]))
    V_section = np.zeros((len(sections), dims[0], dims[2]))
    for index, section in enumerate(sections):
        U_section[index, :, :] = U_trim[:, section - 1, :]
        V_section[index, :, :] = V_trim[:, section - 1, :]

    bathy_array = bathy.variables["Bathymetry"][...].data
    bathy_mask = bathy.variables["Bathymetry"][:].mask
    bathy_array[bathy_mask] = 0

    return SimpleNamespace(
        U_surface=U_surface,
        V_surface=V_surface,
        U_section=U_section,
        V_section=V_section,
        gridX=np.arange(U_surface.shape[1]) + 1,
        gridY=np.arange(U_surface.shape[0]) + 1,
        depth=mesh_mask["gdept_1d"][0, ...],
        bathy_array=bathy_array,
    )


def _prep_fig_axes(figsize, theme, sections=(450,), pos=((0.1, 0.95),)):

    # Make Figure
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"])

    # Make Sections
    ax_section = {}
    for index, section in enumerate(zip(sections, pos)):
        gs = gridspec.GridSpec(2, 1, height_ratios=[1, 2])
        gs.update(
            bottom=section[1][0], top=section[1][1], left=0.1, right=0.5, hspace=0.05
        )
        ax_section[str(section[0])] = [fig.add_subplot(gs[0]), fig.add_subplot(gs[1])]
        for ax, shift, axis in zip(
            ax_section[str(section[0])], [0, 1], ["bottom", "top"]
        ):
            ax.spines[axis].set_visible(False)
            ax.tick_params(which="both", top="off", right="off", direction="out")
            ax.set_facecolor(theme.COLOURS["axes"]["background"])
            theme.set_axis_colors(ax)
        ax_section[str(section[0])][0].tick_params(
            which="both", labelbottom="off", bottom="off"
        )

    # Make Surface
    gs = gridspec.GridSpec(1, 1)
    gs.update(bottom=0.1, top=0.95, left=0.55, right=0.9)
    ax_surface = fig.add_subplot(gs[0])
    viz_tools.set_aspect(ax_surface)
    theme.set_axis_colors(ax_surface)

    # Make Colorbar
    gs = gridspec.GridSpec(1, 1)
    gs.update(bottom=0.03, top=0.04, left=0.1, right=0.5)
    ax_cbar = fig.add_subplot(gs[0])
    theme.set_axis_colors(ax_cbar)

    return fig, (ax_section, ax_surface, ax_cbar)


def _plot_vel_section(
    fig, axs, cax, V, plot_data, bathy, ibreak=24, cmap=None, levels=None
):

    zindex = [slice(None, ibreak + 1), slice(ibreak, None)]
    for ax, iz, ifill in zip(axs, zindex, [ibreak, -1]):
        C = ax.contourf(
            plot_data.gridX,
            plot_data.depth[iz],
            V[iz, :],
            levels,
            cmap=cmap,
            extend="both",
            zorder=0,
        )
        ax.contour(
            plot_data.gridX,
            plot_data.depth[iz],
            V[iz, :],
            levels,
            colors="gray",
            linewidths=0.5,
            zorder=1,
        )
        ax.fill_between(
            plot_data.gridX,
            bathy,
            plot_data.depth[ifill],
            facecolor="burlywood",
            linewidth=0,
            zorder=2,
        )
        ax.plot(plot_data.gridX, bathy, "k-", zorder=3)

    cbar = fig.colorbar(C, cax=cax, orientation="horizontal")

    return cbar


def _cbar_labels(cbar, contour_intervals, theme, label):
    cbar.set_ticks(contour_intervals)
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS["cbar"]["tick labels"])
    cbar.set_label(
        label, fontproperties=theme.FONTS["axis"], color=theme.COLOURS["text"]["axis"]
    )


def _section_axes_labels(
    ax, plot_data, theme, lims=(150, 350, 0, 450), ibreak=24, xlabel=True
):

    # Top panel
    ax[0].set_xlim(lims[:2])
    ax[0].set_ylim([plot_data.depth[ibreak], lims[2]])

    # Bottom panel
    ax[1].set_xlim(lims[:2])
    ax[1].set_ylim([lims[3], plot_data.depth[ibreak]])
    ax[1].set_ylabel(
        "Depth [m]",
        color=theme.COLOURS["text"]["axis"],
        fontproperties=theme.FONTS["axis"],
    )
    ax[1].yaxis.set_label_coords(-0.07, 0.8)
    if xlabel:
        ax[1].set_xlabel(
            "Grid x",
            color=theme.COLOURS["text"]["axis"],
            fontproperties=theme.FONTS["axis"],
        )


def _plot_vel_surface(ax, plot_data, bathy, sections=None):

    ax.quiver(
        plot_data.gridX[::5],
        plot_data.gridY[::5],
        plot_data.U_surface[::5, ::5],
        plot_data.V_surface[::5, ::5],
        scale=20,
    )
    if sections is not None:
        for section in zip(*sections):
            ax.plot(section[1][:2], (section[0], section[0]), "r--", linewidth=2)
    viz_tools.plot_land_mask(ax, bathy, color="burlywood")
    viz_tools.plot_coastline(ax, bathy)


def _surface_axes_labels(ax, theme, lims=(0, 397, 200, 750)):
    ax.set_xlim(lims[:2])
    ax.set_ylim(lims[2:])
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
