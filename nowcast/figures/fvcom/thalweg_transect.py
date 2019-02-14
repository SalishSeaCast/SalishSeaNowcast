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

"""Produce image-loop figures showing vertical transects for variables from
the VHFR FVCOM model domain along several thalweg transects.
"""

from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy
import cmocean

import nowcast.figures.website_theme

from OPPTools.utils import fvcom_postprocess as fpp


def make_figure(
    place,
    time_index,
    fvcom_results_dataset,
    varname,
    figsize=(16, 9),
    theme=nowcast.figures.website_theme,
):
    """Plot thalweg transects for model variables from the VHFR FVCOM model.

    :arg str place: Name of domain sub-area 
    
    :arg int time_index: index of dataset for which to plot data

    :arg fvcom_results_dataset: VHFR FVCOM model flow fields results dataset.
    :type fvcom_stns_dataset: 'netCDF4.Dataset`

    :arg str varname: standard fvcom variable or 'normal velocity' or 'tangential velocity';
                      normal velocity is positive into the page
                      tangential velocity is positive toward the right

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    fig, ax = _prep_fig_axes(figsize, theme)
    plot_data = _prep_plot_data(place, fvcom_results_dataset, time_index, varname)
    cbar = _plot_thalweg(ax, plot_data, theme)
    _set_axes_labels(ax, cbar, plot_data, theme)
    return fig


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"])
    ax = fig.add_subplot(1, 1, 1)
    ax.set_axis_bgcolor(theme.COLOURS["axes"]["background"])
    return fig, ax


def _prep_plot_data(place, fvcom_results_dataset, time_index, varname):

    # Get time stamp from results dataset
    date_bytes = fvcom_results_dataset.variables["Times"][time_index, :]
    date_str = date_bytes.data.tostring().decode("utf-8")
    date = date_str[0:10] + " " + date_str[11:19] + " UTC"

    # Load the rest of the arrays needed
    x = fvcom_results_dataset["x"][:]
    y = fvcom_results_dataset["y"][:]
    h = fvcom_results_dataset["h"][:]
    tri = fvcom_results_dataset["nv"][...].T - 1  # 3-column, zero-based
    siglay = fvcom_results_dataset["siglay"][:]
    siglev = fvcom_results_dataset["siglev"][:]

    # fmt: off
    if place == "Vancouver Harbour":
        xt = [488231.735, 489164.600, 489791.471, 492539.541, 494090.738,
              496814.042, 497666.143, 498271.520, 498919.346, 499575.585,
              500341.197, 501288.236, 502974.669, 504338.308]
        yt = [5462843.199, 5462728.295, 5462608.950, 5460732.559, 5460268.553,
              5460372.070, 5460170.150, 5460240.891, 5460271.740, 5460181.998,
              5460330.633, 5460651.256, 5460316.877, 5460870.514]
        clim = {'salinity':(24, 30), "temp": (5, 10), 'tangential velocity': (-3, 3)}

    if place == "Port Moody":
        xt = [504338.308, 505350.106, 505994.245, 506911.296, 507681.396,
              508673.051, 509396.596, 510689.110]
        yt = [5460870.514, 5460186.615, 5459860.430, 5459857.626, 5460230.616,
              5460350.709, 5460123.549, 5459285.152]
        clim = {'salinity':(22, 27), "temp": (5, 9), 'tangential velocity': (-0.5, 0.5)}
        
    if place == "Indian Arm":
        xt = [504338.308, 504614.340, 505299.179, 506644.379, 507388.050,
              508500.265, 508722.376, 509146.408, 508948.526, 510248.889,
              509733.686, 509069.678, 508427.574]
        yt = [5460870.514, 5462694.832, 5464229.277, 5465152.303, 5466614.650,
              5468046.238, 5468964.879, 5469615.060, 5472405.130, 5475485.044,
              5477079.703, 5478077.966, 5479284.985]
        clim = {'salinity':(24, 29), "temp": (5.5, 9), 'tangential velocity': (-0.75, 0.75)}        

    # fmt: on
    xt, yt = numpy.array(xt), numpy.array(yt)
    vmin, vmax = clim[varname]

    # Calculate transect
    tr = fpp.vertical_transect(xt, yt, x, y, tri, h, siglay, siglev)

    # Interpolate variable onto transect
    xx, zz, vi, _, __, ___ = fpp.vertical_transect_snap(
        fvcom_results_dataset, time_index, varname, tr
    )

    if varname == "salinity":
        longname, units, cmap = "Salinity", "psu", cmocean.cm.haline
    if varname == "temp":
        longname, units, cmap = "Temperature", "Degrees C", cmocean.cm.thermal
    if varname == "tangential velocity":
        longname, units, cmap = "Tangential Velocity", "m/s", cmocean.cm.balance

    return SimpleNamespace(
        xx=xx,
        zz=zz,
        vi=vi,
        varname=varname,
        longname=longname,
        units=units,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        place=place,
        date=date,
    )


def _plot_thalweg(ax, plot_data, theme):

    # use continuous colormap with pcolormesh
    hp = ax.pcolormesh(
        plot_data.xx,
        plot_data.zz,
        plot_data.vi,
        shading="gouraud",
        vmin=plot_data.vmin,
        vmax=plot_data.vmax,
        cmap=plot_data.cmap,
    )
    cbar = plt.colorbar(hp)

    if plot_data.place == "Vancouver Harbour":
        xlim, ylim = [0, 17000], [-65, 5]

    if plot_data.place == "Port Moody":
        xlim, ylim = [0, 7000], [-25, 5]

    if plot_data.place == "Indian Arm":
        xlim, ylim = [0, 22000], [-160, 5]

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    return cbar


def _set_axes_labels(ax, cbar, plot_data, theme):
    ax.set_title(
        f"{plot_data.place} {plot_data.longname} {plot_data.date}",
        fontproperties=theme.FONTS["axes title"],
        color=theme.COLOURS["text"]["axes title"],
    )
    ax.set_xlabel(
        "Distance (m)",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_ylabel(
        "Depth (m)",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    theme.set_axis_colors(ax)

    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS["cbar"]["tick labels"])
    cbar.set_label(
        f"{plot_data.longname} ({plot_data.units})",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
