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

"""Produce image-loop figures showing surface current vectors on a heatmap of
speed for several regions of interest within the VHFR FVCOM model domain.

Testing notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/TestSurfaceCurrents.ipynb
"""

from types import SimpleNamespace

import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import numpy
import warnings

import nowcast.figures.website_theme

from OPPTools.general_utilities import geometry as mgeom
from OPPTools.utils import fvcom_postprocess as fpp


def make_figure(
    place,
    time_index,
    fvcom_results_dataset,
    figsize=(16, 9),
    theme=nowcast.figures.website_theme,
):
    """Plot surface current vectors over a speed colormap for a sub-area of
    the VHFR FVCOM model.

    :arg str place: Name of domain sub-area 
    
    :arg int time_index: index of dataset for which to plot data

    :arg fvcom_results_dataset: VHFR FVCOM model flow fields results dataset.
    :type fvcom_stns_dataset: 'netCDF4.Dataset`

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    fig, ax = _prep_fig_axes(figsize, theme)
    plot_data = _prep_plot_data(place, fvcom_results_dataset, time_index)
    cbar = _plot_surface_currents(ax, plot_data, theme)
    _set_axes_labels(ax, cbar, plot_data, theme)
    return fig


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"])
    ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor(theme.COLOURS["axes"]["background"])
    return fig, ax


def _prep_plot_data(place, fvcom_results_dataset, time_index):

    # Get time stamp from results dataset
    date_bytes = fvcom_results_dataset.variables["Times"][time_index, :]
    date_str = date_bytes.data.tostring().decode("utf-8")
    date = date_str[0:10] + " " + date_str[11:19] + " UTC"

    # Load the rest of the arrays needed
    xc = fvcom_results_dataset["xc"][:]
    yc = fvcom_results_dataset["yc"][:]
    lon = fvcom_results_dataset["lon"][:]
    lat = fvcom_results_dataset["lat"][:]
    lonc = fvcom_results_dataset["lonc"][:]
    latc = fvcom_results_dataset["latc"][:]
    tri = fvcom_results_dataset["nv"][...].T - 1  # 3-column, zero-based
    u = fvcom_results_dataset["u"][time_index, 0, :]
    v = fvcom_results_dataset["v"][time_index, 0, :]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="invalid value encountered in sqrt")
        speed = numpy.sqrt(u * u + v * v)

    # invalidate dry cells
    if "wet_cells" in fvcom_results_dataset.variables:
        wet = fvcom_results_dataset["wet_cells"][time_index, :].astype(bool)
        u[~wet] = numpy.nan
        v[~wet] = numpy.nan

    # decimation radius for arrows (m)
    dthres = 100
    # m/s; to avoid very small arrows or conversion of arrows to dots by plt.quiver
    minarrow = 0.4

    # scale small arrows such that min amplitude is minarrow
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message="divide by zero encountered in true_divide"
        )
        warnings.filterwarnings("ignore", message="invalid value encountered in less")
        warnings.filterwarnings(
            "ignore", message="invalid value encountered in multiply"
        )

        minscale = minarrow / speed
        minscale[minscale < 1] = 1
        u = u * minscale
        v = v * minscale

    # Comnpute vector decimation indices
    iquiver = mgeom.points_decimate(numpy.c_[xc, yc], dthres)

    return SimpleNamespace(
        lon=lon,
        lat=lat,
        lonc=lonc,
        latc=latc,
        tri=tri,
        u=u,
        v=v,
        speed=speed,
        iquiver=iquiver,
        place=place,
        date=date,
    )


def _plot_surface_currents(ax, plot_data, theme):
    # Get color map from OPPTools
    cmap = fpp.get_cmap_speed()

    # for units='inches' in vel_quiver: 1 m/s arrow has length of 1/vscale inches
    vscale = 8

    # m/s; fixed colorscale limits
    vmin, vmax = 0, 3

    # colour-coded speed field
    tpc = ax.tripcolor(
        plot_data.lon,
        plot_data.lat,
        plot_data.tri,
        plot_data.speed,
        cmap=cmap,
        zorder=1,
        vmin=vmin,
        vmax=vmax,
    )
    tpc.cmap.set_under("0.8")  # colour for nans
    cbar = plt.colorbar(tpc)

    # for scale_units='xy' and scale other than 1, quiverkey will not give correct arrow length;
    # use inches to make arrow size consistent across different plots
    quiv = ax.quiver(
        plot_data.lonc[plot_data.iquiver],
        plot_data.latc[plot_data.iquiver],
        plot_data.u[plot_data.iquiver],
        plot_data.v[plot_data.iquiver],
        units="inches",
        scale_units="inches",
        scale=vscale,
        headwidth=2,
        headlength=3.2,
        headaxislength=3,
        zorder=2,
    )
    ax.quiverkey(quiv, 0.93, 0.93, 2, "2 m/s", labelpos="N", coordinates="axes")

    if plot_data.place == "English Bay":
        xlim, ylim = [-123.2713, -123.1332], [49.2704, 49.3420]

    if plot_data.place == "Vancouver Harbour":
        xlim, ylim = [-123.1608, -122.9893], [49.2817, 49.3272]

    if plot_data.place == "Indian Arm":
        xlim, ylim = [-123.0412, -122.8695], [49.2857, 49.3523]

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    ar = 1.0 / numpy.cos(numpy.deg2rad(numpy.mean(ylim)))
    ax.set_aspect(ar)

    ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))

    return cbar


def _set_axes_labels(ax, cbar, plot_data, theme):
    ax.set_title(
        f"{plot_data.place} surface currents {plot_data.date}",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlabel(
        "Longitude",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_ylabel(
        "Latitude",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    theme.set_axis_colors(ax)

    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS["cbar"]["tick labels"])
    cbar.set_label(
        "Speed (m/s)",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
