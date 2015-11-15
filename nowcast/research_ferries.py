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
from __future__ import division, print_function

import datetime
from glob import glob
import os

import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
from pylab import *
import scipy.io as sio

from salishsea_tools import (
    viz_tools,
    tidetools,
)
from salishsea_tools.nowcast import figures


# Font format
title_font = {
    'fontname': 'Bitstream Vera Sans', 'size': '15', 'color': 'black',
    'weight': 'medium'
}
axis_font = {'fontname': 'Bitstream Vera Sans', 'size': '13'}

# Ferry stations
ferry_stations = {'Tsawwassen': {'lat': 49.0084, 'lon': -123.1281},
                  'Duke': {'lat': 49.1632, 'lon': -123.8909},
                  'Vancouver': {'lat': 49.2827, 'lon': -123.1207},
                  'Horseshoe Bay': {'lat': 49.3742, 'lon': -123.2728},
                  'Nanaimo': {'lat': 49.1632, 'lon': -123.8909},
                  'Swartz': {'lat': 48.6882, 'lon': -123.4102}
                  }


def results_dataset_more(period, grid):
    """Return the results dataset for period (e.g. 1h or 1d) and grid
    (e.g. grid_T, grid_U) from results_dir.

    :arg period: 1h or 1d
    :type period: string

    :arg grid: grid_T or grid_U or grid_V for Salish Sea NEMO model.
    :type grid: :class:`netCDF4.Dataset`

    :returns: grid_T or grid_U or grid_V files
    """
    filename_pattern = 'SalishSea_{period}_*_{grid}.nc'
    today = datetime.datetime.today()
    oneday = datetime.timedelta(days=1)
    run_date = today - oneday
    date_str_yesterday = run_date.strftime('%Y%m%d')
    date_str_today = today.strftime('%Y%m%d')
    # Results dataset location
    results_home = '/data/dlatorne/MEOPAR/SalishSea/nowcast/'
    results_dir = os.path.join(results_home, today.strftime('%d%b%y').lower())
    filepaths = glob(
        os.path.join(
            results_dir,
            filename_pattern.format(
                period=period,
                grid=grid)))
    return nc.Dataset(filepaths[0])


def date(year, month, day_start, day_end, period, grid):
    day_range = np.arange(day_start, day_end + 1)
    day_len = len(day_range)
    files_all = [None] * day_len
    inds = np.arange(day_len)

    for i, day in zip(inds, day_range):
        run_date = datetime.datetime(year, month, day)
        results_home = '/data/dlatorne/MEOPAR/SalishSea/nowcast/'
        results_dir = os.path.join(
            results_home,
            run_date.strftime('%d%b%y').lower())
        filename = 'SalishSea_' + period + '_' + \
            run_date.strftime('%Y%m%d').lower(
            ) + '_' + run_date.strftime('%Y%m%d').lower() + '_' + grid + '.nc'
        file_single = os.path.join(results_dir, filename)
        files_all[i] = file_single

    return files_all


def find_dist(q, lon11, lat11, X, Y, bathy, longitude,
              latitude, saline_nemo_3rd, saline_nemo_4rd):
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

    :arg saline_nemo_3rd: 1.5 m depth for 2 or 3 am model salinity
    :type saline_nemo_3rd: numpy array

    :arg saline_nemo_4rd: 1.5 m depth for 3 or 4 am model salinity
    :arg saline_nemo_4rd:numpy array

    :return: integral of model salinity values divided by weights for
            time in saline_nemo_3rd and saline_nemo_4rd respectively.
    """
    grid_T_hr = results_dataset_more('1h', 'grid_T')
    latitude = grid_T_hr.variables['nav_lat']
    longitude = grid_T_hr.variables['nav_lon']

    k = 0
    values = 0
    valuess = 0
    dist = np.zeros(9)
    weights = np.zeros(9)
    value_3rd = np.zeros(9)
    value_4rd = np.zeros(9)

    [x1,
     j1] = tidetools.find_closest_model_point(lon11[q],
                                              lat11[q],
                                              X,
                                              Y,
                                              bathy,
                                              lon_tol=0.0052,
                                              lat_tol=0.00210,
                                              allow_land=False)
    for i in np.arange(x1 - 1, x1 + 2):
        for j in np.arange(j1 - 1, j1 + 2):
            dist[k] = tidetools.haversine(
                lon11[q], lat11[q], longitude[
                    i, j], latitude[
                    i, j])
            weights[k] = 1.0 / dist[k]
            value_3rd[k] = saline_nemo_3rd[i, j] * weights[k]
            value_4rd[k] = saline_nemo_4rd[i, j] * weights[k]
            values = values + value_3rd[k]
            valuess = valuess + value_4rd[k]
            k += 1

    return values, valuess, weights


def salinity_fxn(saline, route_name, today):
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
    struct = (
        ((saline[
            '%s_TSG' %
            route_name])['output'])[
            0,
            0])['Practical_Salinity'][
                0,
        0]
    salinity = struct['data'][0, 0]
    time = struct['matlabTime'][0, 0]
    lonn = struct['longitude'][0, 0]
    latt = struct['latitude'][0, 0]

    a = len(time)
    lon1 = np.zeros([a, 1])
    lat1 = np.zeros([a, 1])
    salinity1 = np.zeros([a, 1])
    if route_name == 'HBDB':
        run_lower = today.replace(hour=2, minute=40, second=0, microsecond=0)
        run_upper = today.replace(hour=4, minute=20, second=0, microsecond=0)
    elif route_name == 'TWDP':
        run_lower = today.replace(hour=3, minute=0, second=0, microsecond=0)
        run_upper = today.replace(hour=5, minute=15, second=0, microsecond=0)
    elif route_name == 'TWSB':
        run_lower = today.replace(hour=2, minute=0, second=0, microsecond=0)
        run_upper = today.replace(hour=4, minute=0, second=0, microsecond=0)
    else:
        print ('This is not a station!')
    for i in np.arange(0, a):
        matlab_datenum = np.float(time[i])
        python_datetime = datetime.datetime.fromordinal(
            int(matlab_datenum)) + timedelta(days=matlab_datenum % 1) - timedelta(days=366)
        if (python_datetime >= run_lower) & (python_datetime <= run_upper):
            lon1[i] = lonn[i]
            lat1[i] = latt[i]
            salinity1[i] = salinity[i]

    mask = lon1[:, 0] != 0
    lon1_2_4 = lon1[mask]
    lat1_2_4 = lat1[mask]
    salinity1_2_4 = salinity1[mask]
    lon11 = lon1_2_4[0:-1:20]
    lat11 = lat1_2_4[0:-1:20]
    salinity11 = salinity1_2_4[0:-1:20]

    bathy, X, Y = tidetools.get_SS2_bathy_data()

    oneday = datetime.timedelta(days=1)
    run_date = today - oneday
    date_str_yesterday = run_date.strftime('%Y%m%d')
    date_str_today = today.strftime('%Y%m%d')

    aa = date(today.year, today.month, today.day, today.day, '1h', 'grid_T')

    date_str_title = today.strftime('%d-%b-%Y')
    tracers = nc.Dataset(aa[0])
    j = int(aa[0][65:67])
    jj = int(aa[0][67:69])
    latitude = tracers.variables['nav_lat'][:]
    longitude = tracers.variables['nav_lon'][:]
    saline_nemo = tracers.variables['vosaline']

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
            q, lon11, lat11, X, Y, bathy, longitude, latitude, saline_nemo_3rd, saline_nemo_4rd)
        value_mean_3rd_hour[q] = values[q] / sum(matrix[q])
        value_mean_4rd_hour[q] = valuess[q] / sum(matrix[q])

    return lon11, lat11, lon1_2_4, lat1_2_4, value_mean_3rd_hour, value_mean_4rd_hour, salinity11, salinity1_2_4, date_str_title


def salinity_ferry_route(route_name):
    """plot daily salinity comparisons between ferry observations and model
    results as well as ferry route with model salinity distribution.

    :arg route_name: route name of these three ferry routes respectively
    :type route_name: string

    :returns: fig
    """
    fig, axs = plt.subplots(1, 2, figsize=(15, 8))

    today = datetime.datetime.today()
    oneday = datetime.timedelta(days=1)
    run_date = today - oneday
    date_str_yesterday = run_date.strftime('%Y%m%d')
    date_str_today = today.strftime('%Y%m%d')

    grid_T_hr = results_dataset_more('1h', 'grid_T')
    filepath_name = date(
        today.year,
        today.month,
        today.day,
        today.day,
        '1h',
        'grid_T')

    latitude = grid_T_hr.variables['nav_lat']
    longitude = grid_T_hr.variables['nav_lon']

    sal_hr = grid_T_hr.variables['vosaline']
    t, z = 3, 1
    sal_hr = np.ma.masked_values(sal_hr[t, z], 0)
    grid_B = nc.Dataset(
        '/data/nsoontie/MEOPAR/NEMO-forcing/grid/bathy_meter_SalishSea2.nc')
    PNW_coastline = sio.loadmat('/ocean/rich/more/mmapbase/bcgeo/PNW.mat')

    figures.plot_map(axs[1], grid_B, PNW_coastline)
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
