#  Copyright 2013 – present The Salish Sea MEOPAR contributors
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
"""Produce a figure that compares salinity at 1.5m depth model results to
salinity observations from the ONC instrument package aboard a BC Ferries
vessel.

Testing notebook for this module is
https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/figures/comparison/TestSalinityFerryTrackModule.ipynb
"""
from collections import namedtuple

import matplotlib.pyplot as plt
import numpy as np
from salishsea_tools import nc_tools, teos_tools, viz_tools

import nowcast.figures.website_theme


def make_figure(grid_T_hr, figsize=(20, 7.5), theme=nowcast.figures.website_theme):
    """Plot salinity comparison of 1.5m depth model results to
    salinity observations from the ONC instrument package aboard a BC Ferries
    vessel as well as ferry route with model salinity distribution.

    :arg grid_T_hr:
    :type grid_T_hr: :py:class:`netCDF4.Dataset`

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    lons, lats, sal_model, sal_obs = _prep_plot_data(grid_T_hr)
    fig, (ax_comp, ax_sal_map) = plt.subplots(
        1, 2, figsize=figsize, facecolor=theme.COLOURS["figure"]["facecolor"]
    )
    _plot_salinity_map(ax_sal_map, lons, lats, sal_model, sal_obs, theme)
    # _plot_salinity_comparison(ax_comp, sal_model, sal_obs, theme)
    return fig


def _prep_plot_data(grid_T_hr):
    si, ei = 200, 610
    sj, ej = 20, 370
    lons = grid_T_hr.variables["nav_lon"][si:ei, sj:ej]
    lats = grid_T_hr.variables["nav_lat"][si:ei, sj:ej]
    model_depth_level = 1  # 1.5 m
    ## TODO: model time step for salinity contour map should be calculated from
    ##       ferry route time
    model_time_step = 3  # 02:30 UTC
    sal_hr = grid_T_hr.variables["vosaline"]
    ## TODO: Use mesh mask instead of 0 for masking
    sal_masked = np.ma.masked_values(
        sal_hr[model_time_step, model_depth_level, si:ei, sj:ej], 0
    )
    timestamped_sal = namedtuple("timestamped_sal", "salinity, timestamp")
    sal_model = timestamped_sal(
        teos_tools.psu_teos(sal_masked), nc_tools.timestamp(grid_T_hr, model_time_step)
    )
    return lons, lats, sal_model, None


def _plot_salinity_map(ax, lons, lats, sal_model, sal_obs, theme):
    ax.set_facecolor(theme.COLOURS["land"])
    cmap = plt.get_cmap("plasma")
    contour_levels = 20
    mesh = ax.contourf(lons, lats, sal_model.salinity, contour_levels, cmap=cmap)
    cbar = plt.colorbar(mesh, ax=ax, shrink=0.965)
    # Plot ferry track
    ## TODO: Handle sal_obs data structure
    # ax.plot(sal_obs, color='black', linewidth=4)
    _salinity_map_place_markers(ax, theme)
    # Format the axes and make it pretty
    _salinity_map_axis_labels(ax, sal_model, theme)
    _salinity_map_cbar_labels(cbar, theme)
    _salinity_map_set_view(ax, lats)


def _salinity_map_place_markers(ax, theme):
    pass


def _salinity_map_axis_labels(ax, sal_model, theme):
    sal_time = sal_model.timestamp.to("local")
    ax.set_title(
        f'1.5m Model Salinity at {sal_time.format("HH:mm")} '
        f"{sal_time.tzinfo.tzname(sal_time.datetime)} and Ferry Track",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_xlabel(
        "Longitude [°E]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_ylabel(
        "Latitude [°N]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    theme.set_axis_colors(ax)


def _salinity_map_cbar_labels(cbar, theme):
    cbar.ax.axes.tick_params(labelcolor=theme.COLOURS["cbar"]["tick labels"])
    cbar.set_label(
        "Absolute Salinity [g/kg]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )


def _salinity_map_set_view(ax, lats):
    viz_tools.set_aspect(ax, coords="map", lats=lats)
    ax.set_xlim(-124.5, -122.5)
    ax.set_ylim(48.3, 49.6)


def _plot_salinity_comparison(ax, sal_model, sal_obs, theme):
    # plot observations for ferry crossing
    # plot model results from time steps that "bracket" observations
    # Format the axes and make it pretty
    _salinity_comparison_axis_labels(ax, theme)
    _salinity_comparison_set_view(ax)


def _salinity_comparison_axis_labels(ax, theme):
    ## TODO: Put time range in title
    # ax.set_title('Surface Salinity: ' + dmy, **theme.FONTS['axes title'])
    ax.set_xlabel(
        "Longitude",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.set_ylabel(
        "Absolute Salinity [g/kg]",
        fontproperties=theme.FONTS["axis"],
        color=theme.COLOURS["text"]["axis"],
    )
    ax.grid(axis="both")
    ax.legend(loc="lower left")
    ## TODO: Perhaps move ONC acknowledgement into frame, just below legend
    ax.text(
        0.25,
        -0.1,
        "Observations from Ocean Networks Canada",
        transform=ax.transAxes,
        color=theme.COLOURS["axis"]["labels"],
    )
    theme.set_axis_colors(ax)


def _salinity_comparison_set_view(ax):
    ax.set_xlim(-124, -123)
    ax.set_ylim(10, 32)
