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

"""Produce 4 figures that show the time series of surface
    - nitrate and diatom concentrations
    - mesozooplankton and microzooplankton concentrations
    - mesodinium and flagellates concentrations
    - temperature and salinity
    over the last 2 months at a time series site.
"""

from types import SimpleNamespace

import matplotlib.pyplot as plt
import xarray as xr
import arrow as arw

from salishsea_tools import places

import nowcast
import nowcast.figures.website_theme

from importlib import reload

def make_figure(
    xr_dataset,
    left_variable,
    right_variable,
    place,
    figsize=(20, 8),
    theme=nowcast.figures.website_theme
):
    """    
    :param xr_dataset: Hourly average 3d biological fields (ubcSSg3DBiologyFields1hV17-02) and tracer fields (ubcSSg3DTracerFields1hV17-02) from the gridapp datasets of the data server ERDAPP (https://salishsea.eos.ubc.ca/erddap/griddap/index.html?page=1&itemsPerPage=1000). 
    :type xr_dataset: :class:`xarray.core.dataset.Dataset`
    
    :param left_variable: One of the data variables among 'nitrate', 'mesozooplankton', 'ciliates', 'temperature'. 
    :type left_variable: :class:`xarray.Variable`

    :param right_variable: One of the data variables among 'diatoms', 'microzooplankton', 'flagellates', 'salinity'. 
    :type right_variable: :class:`xarray.Variable`

    :param place: time series site.
    :type place: :class:`str`
    
    :param 2-tuple figsize: Figure size (width, height) in inches.

    :param theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data(xr_dataset, left_variable, right_variable, place)

    fig, axl, axr = _prep_fig_axes(figsize, theme)
    _plot_timeseries(axl, plot_data.left, left_variable, theme)
    _plot_timeseries(axr, plot_data.right, right_variable, theme)
    _timeseries_axes_labels(axl, axr, left_variable, plot_data.left_long_name, plot_data.left_units, 
                            right_variable, plot_data.right_long_name, plot_data.right_units, theme)

    return fig



def _prep_plot_data(xr_dataset, left_variable, right_variable, place):

    Dday=xr_dataset.time_coverage_end
    EndDay = arw.get(Dday)
    StartDay = EndDay.replace(months=-2)
    time_slice = slice(StartDay.date(),EndDay.date(),6)

    gridY = places.PLACES[place]['NEMO grid ji'][0]
    gridX = places.PLACES[place]['NEMO grid ji'][1]

    left = xr_dataset[left_variable].sel(time=time_slice).isel(depth=0).isel(
        gridX=gridX).isel(gridY=gridY)
    
    right = xr_dataset[right_variable].sel(time=time_slice).isel(depth=0).isel(
        gridX=gridX).isel(gridY=gridY)
    
    left_long_name = xr_dataset[left_variable].long_name
    left_units = xr_dataset[left_variable].units
    
    right_long_name = xr_dataset[right_variable].long_name
    right_units = xr_dataset[right_variable].units
    

    return SimpleNamespace(left=left, 
                           right=right, 
                           left_long_name=left_long_name, 
                           left_units=left_units,
                           right_long_name=right_long_name, 
                           right_units=right_units
                          )


def _prep_fig_axes(figsize, theme):
    fig, axl = plt.subplots(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])

    axl.set_axis_bgcolor(theme.COLOURS['axes']['background'])
    axr = axl.twinx()
    axr.set_axis_bgcolor(theme.COLOURS['axes']['background'])
    
    return fig, axl, axr


def _plot_timeseries(ax, plot_data, variable, theme):
    ax.plot(plot_data.time, plot_data, color=theme.COLOURS['time series'][variable])
    return

def _timeseries_axes_labels(axl, axr, left_variable, left_long_name, left_units, 
                            right_variable, right_long_name, right_units, theme):
    axl.set_xlabel(
        'Date',
        color=theme.COLOURS['text']['axis'],
        fontproperties=theme.FONTS['axis'])
    axl.set_ylabel(left_long_name+' ['+left_units+']', fontproperties=theme.FONTS['axis'])
    theme.set_axis_colors(axl)
    axr.set_ylabel(right_long_name+' ['+right_units+']', fontproperties=theme.FONTS['axis']
                   ,rotation=-90, verticalalignment='bottom')
    theme.set_axis_colors(axr)

    axl.text(
        0.5,
        0.95,
        left_long_name,
        horizontalalignment='center',
        color=theme.COLOURS['time series'][left_variable],
        fontproperties=theme.FONTS['legend label large'],
        transform=axl.transAxes)
    axl.text(
        0.5,
        0.9,
        right_long_name,
        horizontalalignment='center',
        color=theme.COLOURS['time series'][right_variable],
        fontproperties=theme.FONTS['legend label large'],
        transform=axl.transAxes)
    
    axl.grid(axis='x')
    