# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

"""Produce a figure that shows a map of the Salish Sea with markers indicating
the risks of high water levels at the Point Atkinson, Victoria, Campbel River,
Nanaimo, and Cherry Point tide gauge locations.
The figure also shows wind vectors that indicate the average wind speed and
direction averaged over the 4 hours preceding the maximum sea surface height.
Text below the map provides quantitative information about the maximum water
level, when it occurs, and the 4 hr averaged wind speed, as well as
acknowledgement of data sources.
"""
from collections import namedtuple

from matplotlib import gridspec
import matplotlib.pyplot as plt
import numpy as np

from salishsea_tools import (
    nc_tools,
    teos_tools,
    viz_tools,
)

from nowcast.figures import shared
import nowcast.figures.website_theme


def storm_surge_alerts(
    bathy, grid_T_hr, grids_15m, weather_path, coastline, tidal_preductions,
    figsize=(18, 20),
    theme=nowcast.figures.website_theme,
):
    """Plot high water level risk indication markers and 4h average wind
    vectors on a Salish Sea map with summary text below.

    :arg bathy: Bathymetry dataset for the Salish Sea NEMO model.
    :type bathy: :py:class:`netCDF4.Dataset`

    :arg grid_T_hr: Hourly tracer results dataset from the Salish Sea NEMO
                    model.
    :type grid_T_hr: :py:class:`netCDF4.Dataset`

    :arg dict grids_15m: Collection of 15m sea surface height datasets at tide
                         gauge locations,
                         keyed by tide gauge station name.
    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    arg str tidal_predications: Path to directory of tidal prediction
                                 file.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    _prep_plot_data()
    fig, (ax_map, ax_pa_info, ax_cr_info, ax_vic_info) = _prep_fig_axes(
        figsize, theme)
    _plot_alerts_map(ax_map, coastline)
    info_boxes = (ax_pa_info, ax_cr_info, ax_vic_info)
    info_places = ('Point Atkinson', 'Campbell River', 'Victoria')
    for ax, place in zip(info_boxes, info_places):
        _plot_info_box(ax, place)
    return fig


def _prep_plot_data():
    pass


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])
    gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 1], height_ratios=[6, 1])
    gs.update(hspace=0.1, wspace=0.05)
    ax_map = fig.add_subplot(gs[0, :])
    ax_pa_info = fig.add_subplot(gs[1, 0])
    ax_cr_info = fig.add_subplot(gs[1, 1])
    ax_vic_info = fig.add_subplot(gs[1, 2])
    return fig, (ax_map, ax_pa_info, ax_cr_info, ax_vic_info)


def _plot_alerts_map(ax, coastline):
    shared.plot_map(ax, coastline)


def _plot_info_box(ax, place):
    pass
