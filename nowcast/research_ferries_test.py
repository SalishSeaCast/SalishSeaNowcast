# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""A collection of Python functions to produce comparisons between with the
salinity of British Columbia ferry observations data and the model results with
visualization figures for analysis of daily nowcast runs.
"""
import datetime
from glob import glob
import os

import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
import pandas as pd
import scipy.io as sio

from salishsea_tools import (
    viz_tools,
    tidetools,
)

from nowcast import figures


# Font format
title_font = {
    'fontname': 'Bitstream Vera Sans', 'size': '15', 'color': 'black',
    'weight': 'medium'
}
axis_font = {'fontname': 'Bitstream Vera Sans', 'size': '13'}

# Ferry stations
ferry_stations = {'Tsawwassen': {'lat': 49.0084,
                                 'lon': -123.1281},
                  'Duke': {'lat': 49.1632,
                           'lon': -123.8909},
                  'Vancouver': {'lat': 49.2827,
                                'lon': -123.1207},
                  'Horseshoe Bay': {'lat': 49.3742,
                                    'lon': -123.2728},
                  'Nanaimo': {'lat': 49.1632,
                              'lon': -123.8909},
                  'Swartz': {'lat': 48.6882,
                             'lon': -123.4102}
                  }

route = {'HBDB': {'start': {'hour': 2,
                            'minute': 40},
                  'end': {'hour': 4,
                          'minute': 20}},
         'TWDP': {'start': {'hour': 3,
                            'minute': 0},
                  'end': {'hour': 5,
                          'minute': 15}},
         'TWSB': {'start': {'hour': 2,
                            'minute': 0},
                  'end': {'hour': 4,
                          'minute': 0}}
         }


def model_IDW(obs, bathy, grid_T_hr, sal_a, sal_b):
    """Perform a inverse distance weighted (IDW) interpolation with 8 nearest
    points to the model value that is nearest to a ferry observation point.

    :arg obs: Array containing time, lon, lat and salinity or a single point
    :type obs: numpy array

    :arg bathy: model bathymetry
    :type bathy: numpy array

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg sal_a: 1.5 m depth for 3 am (if TWDP route, 2am)
    :type sal_a: numpy array

    :arg sal_b: 1.5 m depth for 4 am (if TWDP route, 3am)
    :arg sal_b: numpy array

    :return: integral of model salinity values divided by weights for
            sal_a and sal_b.
    """
    Y = grid_T_hr.variables['nav_lat']
    X = grid_T_hr.variables['nav_lon']

    # Find nearest model point to a ferry route point
    [x1, y1] = tidetools.find_closest_model_point(obs[1],
                                                  obs[2],
                                                  X,
                                                  Y,
                                                  bathy)

    # Inverse distance weighted interpolation with the 8 nearest model values.
    val_a_sum = 0
    val_b_sum = 0
    weight_sum = 0

    for i in np.arange(x1 - 1, x1 + 2):
        for j in np.arange(y1 - 1, y1 + 2):
            dist = tidetools.haversine(
                obs[1], obs[2], X[i, j], Y[i, j])
            weight = 1.0 / dist
            weight_sum = weight_sum + weight
            val_a = sal_a[i, j] * weight
            val_b = sal_b[i, j] * weight
            val_a_sum = val_a_sum + val_a
            val_b_sum = val_a_sum + val_b

    sal_a_idw = val_a_sum / weight_sum
    sal_b_idw = val_b_sum / weight_sum

    return sal_a_idw, sal_b_idw


def ferry_salinity(route_name, dmyf, dmy, step=20):
    """Load ferry data and slice it to contain only the during route values.

    :arg route_name: name of a ferre route. HBDB, TWDP or TWSB.
    :type route_name: string

    :arg dmy: today's date in ddmonyy format
    :type dmy: string

    :arg step: selecting every nth data point
    :type step: int

    return matrix containing time, lon, lat and salinity of ferry observations
    """
    # Load observation ferry salinity data with locations and time
    obs = _get_sal_data(route_name, dmyf)

    # Create datetime object for start and end of route times
    date = datetime.datetime.strptime(dmy, '%d%b%y')
    start_time = date.replace(
        hour=route[route_name]['start']['hour'],
        minute=route[route_name]['start']['minute'])
    end_time = date.replace(
        hour=route[route_name]['end']['hour'],
        minute=route[route_name]['end']['minute'])

    # Slice the observational arrays to only have "during route" data
    time_obs = datenum2datetime(obs[0])
    df = pd.DataFrame(time_obs)
    j = np.logical_and(df >= start_time, df <= end_time)
    j = np.array(j)
    obs_route = obs[0:4, j]

    # High frequency ferry data, take every 20th value
    obs_slice = obs_route[:, 0:-1:step]

    return obs_slice


def _get_nemo_salinity(route_name, grid_T_hr):
    """Load and select the salinity value of the ferry route time."""
    sal_nemo = grid_T_hr.variables['vosaline']

    if route_name == 'TWSB':
        sal3 = sal_nemo[2, 1, :, :]
        sal4 = sal_nemo[3, 1, :, :]
    else:
        sal3 = sal_nemo[3, 1, :, :]
        sal4 = sal_nemo[4, 1, :, :]

    return sal3, sal4


def _get_sal_data(route_name, dmy):
    """ Retrieve the ferry route data from matlab.

    :arg route_name: name for one of three ferry routes
    :type route_name: string

    :arg date: date in form ddmonyy
    :type date: string

    return list containing time_obs, lon_obs, lat_obs, sal_obs
    """

    date = datetime.datetime.strptime(dmy, "%d%b%y")
    date = date.strftime('%Y%m%d')

    saline = sio.loadmat(
        '/ocean/jieliu/research/meopar/ONC_ferries/%s/%s_TSG%s.mat' % (
            route_name, route_name, date))
    struct = (
        ((saline['%s_TSG' % route_name])
            ['output'])[0, 0])['Practical_Salinity'][0, 0]

    # Assigns variable for the samples data and location
    sal_obs = struct['data'][0, 0]
    time_obs = struct['matlabTime'][0, 0]
    lon_obs = struct['longitude'][0, 0]
    lat_obs = struct['latitude'][0, 0]

    obs = np.array([time_obs[:], lon_obs[:], lat_obs[:], sal_obs[:]])

    return obs


def datenum2datetime(datenum):
    """Convert MATLAB datenum array into python Datetime array."""

    timearray = []
    for mattime, count in zip(datenum, np.arange(len(datenum))):
        time = datetime.datetime.fromordinal(
            int(mattime[0])) + datetime.timedelta(
            days=mattime[0] % 1) - datetime.timedelta(days=366)
        timearray.append(time)

    return timearray


def nemo_sal_route(grid_T_hr, bathy, route_name, obs_sal):
    """Get the salanity data form the NEMO run that matches the time and
    locations of the ferry route by integrated distance weighted interpolation."""

    # Get the salinity data
    sal_a, sal_b = _get_nemo_salinity(route_name, grid_T_hr)

    sal_a_route = np.zeros(obs_sal.shape[1])
    sal_b_route = np.zeros(obs_sal.shape[1])

    # Perform the IDW on each data point and put them into an array for
    # the whole route.
    for i in np.arange(obs_sal.shape[1]):
        sal_a_route[i], sal_b_route[i] = model_IDW(
            obs_sal[:, i], bathy, grid_T_hr, sal_a, sal_b)

    return sal_a_route, sal_b_route


def salinity_ferry_route(
        grid_T_hr, grid_B, bathy, coastline, route_name, dmyf, dmy):
    """plot daily salinity comparisons between ferry observations and model
    results as well as ferry route with model salinity distribution.

    :arg route_name: route name of these three ferry routes respectively
    :type route_name: string

    :returns: fig
    """
    fig, axs = plt.subplots(1, 2, figsize=(15, 8))

    lat = grid_T_hr.variables['nav_lat']
    lon = grid_T_hr.variables['nav_lon']

    # Salinity over the whole domain
    sal_hr = grid_T_hr.variables['vosaline']
    t, z = 3, 1
    sal_hr = np.ma.masked_values(sal_hr[t, z], 0)

    # Load ferry route salinity
    obs_sal = ferry_salinity(route_name, dmyf, dmy)

    # Load model salinity for ferry route
    nemo_a, nemo_b = nemo_sal_route(grid_T_hr, bathy, route_name, obs_sal)

    figures.plot_map(axs[1], grid_B, coastline)
    axs[1].set_xlim(-124.5, -122.5)
    axs[1].set_ylim(48.2, 49.6)
    viz_tools.set_aspect(axs[1], coords='map', lats=lat)
    cmap = plt.get_cmap('spectral')
    cmap.set_bad('burlywood')
    mesh = axs[1].contourf(lon[:], lat[:], sal_hr[:], 10, cmap=cmap)
    cbar = fig.colorbar(mesh)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    cbar.set_label('Pratical Salinity', color='white')

    axs[1].set_title('Ferry Route: 3am[UTC] 1.5m model result ', **title_font)

    bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.7)
    if route_name == 'HBDB':
        stations = ['Horseshoe Bay', 'Nanaimo', 'Vancouver']
    elif route_name == 'TWDP':
        stations = ['Tsawwassen', 'Duke', 'Vancouver']
    elif route_name == 'TWSB':
        stations = ['Tsawwassen', 'Swartz', 'Vancouver']

    for stn in stations:
        axs[1].plot(
            ferry_stations[stn]['lon'],
            ferry_stations[stn]['lat'],
            marker='D',
            color='white',
            markersize=10,
            markeredgewidth=2)

    axs[1].annotate(
        stations[0],
        (ferry_stations[
            stations[0]]['lon'] +
            0.02,
            ferry_stations[
            stations[0]]['lat'] +
            0.12),
        fontsize=15,
        color='black',
        bbox=bbox_args)
    axs[1].annotate(
        stations[1],
        (ferry_stations[
            stations[1]]['lon'] -
            0.55,
            ferry_stations[
            stations[1]]['lat']),
        fontsize=15,
        color='black',
        bbox=bbox_args)
    axs[1].annotate(
        stations[2],
        (ferry_stations[
            stations[2]]['lon'],
            ferry_stations[
            stations[2]]['lat'] +
            0.09),
        fontsize=15,
        color='black',
        bbox=bbox_args)

    figures.axis_colors(axs[1], 'white')

    axs[1].plot(obs_sal[1], obs_sal[2], 'black', linewidth=4)
    if route_name == 'TWSB':
        label_a = '2 am [UTC]'
        label_b = '3 am [UTC]'
    else:
        label_a = '3 am [UTC]'
        label_b = '4 am [UTC]'

    axs[0].plot(obs_sal[1], nemo_a, 'DodgerBlue', linewidth=2, label=label_a)
    axs[0].plot(obs_sal[1], nemo_b, 'MediumBlue',linewidth=2, label=label_b)


    axs[0].plot(
        obs_sal[1],
        obs_sal[3],
        'DarkGreen',
        linewidth=2,
        label="Observed")
    axs[0].text(0.25, -0.1, 'Observations from Ocean Networks Canada',
                transform=axs[0].transAxes, color='white')

    axs[0].set_xlim(-124, -123)
    axs[0].set_ylim(5, 32)
    axs[0].set_title('Surface Salinity: ' + dmy, **title_font)
    axs[0].set_xlabel('Longitude', **axis_font)
    axs[0].set_ylabel('Practical Salinity', **axis_font)
    axs[0].legend(loc=3)
    axs[0].grid()

    fig.patch.set_facecolor('#2B3E50')
    figures.axis_colors(axs[0], 'gray')

    return fig
