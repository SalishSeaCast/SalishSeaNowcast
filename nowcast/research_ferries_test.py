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


def find_dist(q, lon11, lat11, bathy, grid_T_hr, saline_nemo_a, saline_nemo_b):
    """This function is used to calculate the integral of model salinity
    values divided by distance between this model point and observation
    point, weights for each observation point that they hold for its
    surrounding model points.

    :arg q: total number of observation grid points on the ferry track
    :type q: numpy.integer

    :arg lon11: longitude of observation grid points on the ferry track
    :type lon11: numpy array

    :arg lat11: latitude of observation grid points on the ferry track
    :type lat11: numpy array

    :arg bathy: model bathymetry
    :type bathy: numpy array

    :arg longitude: longitude of grid_T in the model
    :type longitude: numpy array

    :arg latitude: latitude of grid_T in the model
    :type latitude: numpy array

    :arg saline_nemo_1: 1.5 m depth for 2 or 3 am model salinity
    :type saline_nemo_3rd: numpy array

    :arg saline_nemo_2: 1.5 m depth for 3 or 4 am model salinity
    :arg saline_nemo_4rd:numpy array

    :return: integral of model salinity values divided by weights for
            time in saline_nemo_3rd and saline_nemo_4rd respectively.
    """
    Y = grid_T_hr.variables['nav_lat']
    X = grid_T_hr.variables['nav_lon']

    k = 0
    values = 0
    valuess = 0
    dist = np.zeros(9)
    weights = np.zeros(9)
    value_3rd = np.zeros(9)
    value_4rd = np.zeros(9)

    [x1, j1] = tidetools.find_closest_model_point(lon11[q],
                                                 lat11[q],
                                                 X,
                                                 Y,
                                                 bathy,
                                                 lat_tol=0.00210)
    for i in np.arange(x1 - 1, x1 + 2):
        for j in np.arange(j1 - 1, j1 + 2):
            dist[k] = tidetools.haversine(
                lon11[q], lat11[q], X[
                    i, j], Y[
                    i, j])
            weights[k] = 1.0 / dist[k]
            value_a[k] = saline_nemo_a[i, j] * weights[k]
            value_b[k] = saline_nemo_b[i, j] * weights[k]
            values = values + value_3rd[k]
            valuess = valuess + value_4rd[k]
            k += 1

    return values, valuess, weights


def salinity_fxn(route_name, bathy, grid_T_hr, dmy):
    """This function was made to return several outputs to make the plot
    finally, for exmaple, longitude, latitude and salinity values of grid
    points for both observations and model.

    :arg saline: daily ferry salinity file
    :type saline: dictionary of .mat file loaded from matlab

    :arg route_name: name for one of three ferry routes
    :type route_name: string

    :arg today: today's datetime
    :type today: datetime.datetime
    """
    # Load observation ferry salinity data with locations and time
    obs = _get_sal_data(route_name, dmy)

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
    j = np.logical_and(df>start_time, df<end_time)
    j = np.array(j)
    obs_route = obs[0:4,j]

    # High frequency ferry data, take every 20th value
    obs_slice = obs_route[:, 0:-1:20]


    saline_nemo = grid_T_hr.variables['vosaline']

    if route_name == 'TWSB':
        saline_nemo_3rd = saline_nemo[2, 1, 0:898, 0:398]
        saline_nemo_4rd = saline_nemo[3, 1, 0:898, 0:398]
    else:
        saline_nemo_3rd = saline_nemo[3, 1, 0:898, 0:398]
        saline_nemo_4rd = saline_nemo[4, 1, 0:898, 0:398]

    matrix = np.zeros([len(lon11), 9])
    values = np.zeros([len(lon11), 1])
    valuess = np.zeros([len(lon11), 1])
    value_mean_3rd_hour = np.zeros([len(lon11), 1])
    value_mean_4rd_hour = np.zeros([len(lon11), 1])
    for q in np.arange(0, len(lon11)):
        values[q], valuess[q], matrix[
            q, :] = find_dist(
            q, lon11, lat11, bathy, grid_T_hr, saline_nemo_3rd, saline_nemo_4rd)
        value_mean_3rd_hour[q] = values[q] / sum(matrix[q])
        value_mean_4rd_hour[q] = valuess[q] / sum(matrix[q])

    return lon11, lat11, lon1_2_4, lat1_2_4, value_mean_3rd_hour, value_mean_4rd_hour, salinity11, salinity1_2_4, date_str_title


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


def salinity_ferry_route(grid_T_hr, bathy, coastline, route_name):
    """plot daily salinity comparisons between ferry observations and model
    results as well as ferry route with model salinity distribution.

    :arg route_name: route name of these three ferry routes respectively
    :type route_name: string

    :returns: fig
    """
    fig, axs = plt.subplots(1, 2, figsize=(15, 8))

    latitude = grid_T_hr.variables['nav_lat']
    longitude = grid_T_hr.variables['nav_lon']

    sal_hr = grid_T_hr.variables['vosaline']
    t, z = 3, 1
    sal_hr = np.ma.masked_values(sal_hr[t, z], 0)

    figures.plot_map(axs[1], bathy, coastline)
    axs[1].set_xlim(-124.5, -122.5)
    axs[1].set_ylim(48.2, 49.6)
    viz_tools.set_aspect(axs[1], coords='map', lats=latitude)
    cmap = plt.get_cmap('spectral')
    cmap.set_bad('burlywood')
    mesh = axs[1].contourf(longitude[:], latitude[:], sal_hr[:], 10, cmap=cmap)
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

    saline = sio.loadmat(
        '/data/jieliu/MEOPAR/FerrySalinity/%s/%s_TSG%s.mat' %
        (route_name, route_name, date_str_yesterday))

    lon11, lat11, lon1_2_4, lat1_2_4, value_mean_3rd_hour, value_mean_4rd_hour, salinity11, salinity1_2_4, date_str_title = salinity_fxn(
        saline, route_name, today)
    axs[1].plot(lon11, lat11, 'black', linewidth=4)
    if route_name == 'TWSB':
        model_salinity_3rd_hour = axs[0].plot(lon11, value_mean_3rd_hour, 'DodgerBlue',
                                              linewidth=2, label='2 am [UTC]')
        model_salinity_4rd_hour = axs[0].plot(lon11, value_mean_4rd_hour, 'MediumBlue',
                                              linewidth=2, label="3 am [UTC]")
    else:
        model_salinity_3rd_hour = axs[0].plot(lon11, value_mean_3rd_hour, 'DodgerBlue',
                                              linewidth=2, label='3 am [UTC]')
        model_salinity_4rd_hour = axs[0].plot(lon11, value_mean_4rd_hour, 'MediumBlue',
                                              linewidth=2, label="4 am [UTC]")

    observation_salinity = axs[0].plot(
        lon1_2_4,
        salinity1_2_4,
        'DarkGreen',
        linewidth=2,
        label="Observed")
    axs[0].text(0.25, -0.1, 'Observations from Ocean Networks Canada',
                transform=axs[0].transAxes, color='white')

    axs[0].set_xlim(-124, -123)
    axs[0].set_ylim(5, 32)
    axs[0].set_title('Surface Salinity: ' + date_str_title, **title_font)
    axs[0].set_xlabel('Longitude', **axis_font)
    axs[0].set_ylabel('Practical Salinity', **axis_font)
    axs[0].legend(loc=3)
    axs[0].grid()

    fig.patch.set_facecolor('#2B3E50')
    figures.axis_colors(axs[0], 'gray')

    return fig
