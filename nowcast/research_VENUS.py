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
VENUS nodes and the model results with visualization figures for analysis
of daily nowcast/forecast runs.
"""
import datetime
from io import StringIO

from dateutil import tz
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import numpy as np
import pandas as pd
import requests
import netCDF4 as nc

from salishsea_tools import (
    nc_tools,
    tidetools as tt,
    viz_tools
)
from salishsea_tools.nowcast import (figures, analyze)

# Font format
title_font = {
    'fontname': 'Bitstream Vera Sans', 'size': '15', 'color': 'white',
    'weight': 'medium'
}
axis_font = {'fontname': 'Bitstream Vera Sans', 'size': '13', 'color': 'white'}

# Constants defined for the VENUS nodes
# Lat/lon/depth from the VENUS website. Depth is in meters.
# i,j are python grid coordinates as returned from
# tidetools.find_closest_model_point()
SITES = {
    'Vancouver': {
        'lat': 49.2827,
        'lon': -123.1207},
    'VENUS': {
        'East': {
            'lat': 49.0419,
            'lon': -123.3176,
            'depth': 170,
            'i': 283,
            'j': 416},
        'Central': {
            'lat': 49.0401,
            'lon': -123.4261,
            'depth': 300,
            'i': 266,
            'j': 424},
        'ddl': {
            'lat': 49.0807167,
            'lon': -123.3400617,
            'depth': 150,
            'i': 284,
            'j': 425}
        }
    }

# Tide correction for amplitude and phase set to September 10th 2014 by nowcast
# Values for there and other constituents can be found in:
# /data/dlatorne/MEOPAR/SalishSea/nowcast/08jul15/ocean.output/
CorrTides = {
    'K1': {
        'freq': 15.041069000,
        'ft': 0.891751,
        'uvt': 262.636797},
    'M2': {
        'freq': 28.984106,
        'ft': 1.035390,
        'uvt': 346.114490}
    }


def dateparse(s):
    """Parse the dates from the VENUS files."""

    unaware = datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')
    aware = unaware.replace(tzinfo=tz.tzutc())

    return aware


def load_VENUS(station):
    """Loads the most recent State of the Ocean data from the VENUS node
    indicated by station.

    This data set includes pressure, temperature, and salinity among
    other things.
    See: http://venus.uvic.ca/research/state-of-the-ocean/

    :arg station: The name of the station, either "East" or "Central".
    :type station: string

    :returns: DataFrame (data) with the VENUS data
    """

    # Define location
    filename = ('SG-{0}/VSG-Strait_of_Georgia_{0}'
                '-VIP-State_of_Ocean.txt'.format(station))

    # Access website
    url = 'http://venus.uvic.ca/scripts/log_download.php'
    params = {
        'userid': 'nsoontie@eos.ubc.ca',
        'filename': filename,
    }
    response = requests.get(url, params=params)

    # Parse data
    fakefile = StringIO(response.content)
    data = pd.read_csv(
        fakefile, delimiter=' ,', skiprows=17,
        names=[
            'date', 'pressure', 'pflag', 'temp', 'tflag', 'sal', 'sflag',
            'sigmaT', 'stflag', 'oxygen', 'oflag',
        ],
        parse_dates=['date'], date_parser=dateparse, engine='python')

    return data


def plot_VENUS(ax_sal, ax_temp, station, start, end):
    """Plots a time series of the VENUS data over a date range.

    :arg ax_sal: The axis in which the salinity is displayed.
    :type ax_sal: axis object

    :arg ax_temp: The axis in which the temperature is displayed.
    :type ax_temp: axis object

    :arg station: The name of the station, either "East" or "Central".
    :type station: string

    :arg start: The start date of the plot.
    :type start: datetime object

    :arg end: The end date of the plot.
    :type end: datetime object

    """

    data = load_VENUS(station)
    ax_sal.plot(data.date[:], data.sal, 'r-', label='Observations')
    ax_sal.set_xlim([start, end])
    ax_temp.plot(data.date[:], data.temp, 'r-', label='Observations')
    ax_temp.set_xlim([start, end])


def compare_VENUS(station, grid_T, grid_B, figsize=(6, 10)):
    """Compares the model's temperature and salinity with observations from
    VENUS station.

    :arg station: Name of the station ('East' or 'Central')
    :type station: string

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg figsize: Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    # Time range
    t_orig, t_end, t = figures.get_model_time_variables(grid_T)

    # Bathymetry
    bathy, X, Y = tt.get_bathy_data(grid_B)

    # VENUS data
    fig, (ax_sal, ax_temp) = plt.subplots(2, 1, figsize=figsize, sharex=True)
    fig.patch.set_facecolor('#2B3E50')
    fig.autofmt_xdate()
    lon = SITES['VENUS'][station]['lon']
    lat = SITES['VENUS'][station]['lat']
    depth = SITES['VENUS'][station]['depth']

    # Plotting observations
    plot_VENUS(ax_sal, ax_temp, station, t_orig, t_end)

    # Grid point of VENUS station
    [j, i] = tt.find_closest_model_point(
        lon, lat, X, Y, bathy, allow_land=True)

    # Model data
    sal = grid_T.variables['vosaline'][:, :, j, i]
    temp = grid_T.variables['votemper'][:, :, j, i]
    ds = grid_T.variables['deptht']

    # Interpolating data
    salc = []
    tempc = []
    for ind in np.arange(0, sal.shape[0]):
        salc.append(figures.interpolate_depth(sal[ind, :], ds, depth))
        tempc.append(figures.interpolate_depth(temp[ind, :], ds, depth))

    # Plot model data
    ax_sal.plot(t, salc, '-b', label='Model')
    ax_temp.plot(t, tempc, '-b', label='Model')

    # Axis
    ax_sal.set_title('VENUS {} - {}'.format(station, t[0].strftime('%d-%b-%Y'),
                                            **title_font))
    ax_sal.set_ylim([29, 32])
    ax_sal.set_ylabel('Practical Salinity [psu]', **axis_font)
    ax_sal.legend(loc=0)
    ax_temp.set_ylim([7, 13])
    ax_temp.set_xlabel('Time [UTC]', **axis_font)
    ax_temp.set_ylabel('Temperature [deg C]', **axis_font)
    figures.axis_colors(ax_sal, 'gray')
    figures.axis_colors(ax_temp, 'gray')

    # Text box
    ax_temp.text(0.25, -0.3, 'Observations from Ocean Networks Canada',
                 transform=ax_temp.transAxes, color='white')

    return fig


def unstag_rot(ugrid, vgrid):
    """Interpolate u and v component values to values at grid cell centre.
    Then rotates the grid cells to align with N/E orientation.

    :arg ugrid: u velocity component values with axes (..., y, x)
    :type ugrid: :py:class:`numpy.ndarray`

    :arg vgrid: v velocity component values with axes (..., y, x)
    :type vgrid: :py:class:`numpy.ndarray`

    :arg station: Name of the station ('East' or 'Central')
    :type station: string

    :returns u_E, v_N, depths: u_E and v_N velocties is the North and East
     directions at the cell center,
    and the depth of the station
    """

    # We need to access the u velocity that is between i and i-1
    u_t = (ugrid[..., 1:, :-1] + ugrid[..., 1:, 1:]) / 2
    v_t = (vgrid[..., 1:, 1:] + vgrid[..., :-1, 1:]) / 2

    theta = 29
    theta_rad = theta * np.pi / 180

    u_E = u_t * np.cos(theta_rad) - v_t * np.sin(theta_rad)
    v_N = u_t * np.sin(theta_rad) + v_t * np.cos(theta_rad)

    return u_E, v_N


def plot_vel_NE_gridded(station, grid, figsize=(14, 10)):
    """Plots the hourly averaged North/South and East/West velocities at a chosen
    VENUS node station using data that is calculated every 15 minutes.

    :arg station: Name of the station ('East' or 'Central')
    :type station: string

    :arg grid: Quarter-hourly velocity and tracer results dataset from NEMO.
    :type grid: :class:`netCDF4.Dataset`

    :arg figsize: Figure size (width, height) in inches or 'default'.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """
    u_u = grid.variables['vozocrtx']
    v_v = grid.variables['vomecrty']
    w_w = grid.variables['vovecrtz']
    dep_t = grid.variables['depthv']
    dep_w = grid.variables['depthw']

    u_E, v_N = unstag_rot(u_u, v_v)
    u_E = u_E[..., 0, 0]
    v_N = v_N[..., 0, 0]

    fig, (axu, axv, axw) = plt.subplots(3, 1, figsize=figsize, sharex=True)
    fig.patch.set_facecolor('#2B3E50')

    max_array = np.maximum(abs(v_N), abs(u_E))
    max_speed = np.amax(max_array)
    vmax = max_speed
    vmin = - max_speed
    step = 0.03

    # viz_tools.set_aspect(axu)
    timestamp = nc_tools.timestamp(grid, 0)
    cmap = plt.get_cmap('jet')
    dep_s = SITES['VENUS'][station]['depth']

    axu.invert_yaxis()
    mesh = axu.contourf(
        np.arange(0, 24, 0.25),
        dep_t[:],
        u_E.transpose(),
        np.arange(vmin, vmax, step), cmap=cmap)
    cbar = fig.colorbar(mesh, ax=axu)
    axu.set_ylim([dep_s, 0])
    axu.set_xlim([0, 23])
    axu.set_ylabel('Depth [m]', **axis_font)
    figures.axis_colors(axu, 'white')
    axu.set_title('East/West Velocities at VENUS {node} on {date}'.format(
        node=station, date=timestamp.format('DD-MMM-YYYY')), **title_font)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    cbar.set_label('[m/s]', **axis_font)

    axv.invert_yaxis()
    mesh = axv.contourf(
        np.arange(0, 24, 0.25),
        dep_t[:],
        v_N.transpose(),
        np.arange(vmin, vmax, step),
        cmap=cmap)
    cbar = fig.colorbar(mesh, ax=axv)
    axv.set_ylim([dep_s, 0])
    axv.set_xlim([0, 23])
    axv.set_ylabel('Depth [m]', **axis_font)
    figures.axis_colors(axv, 'white')
    axv.set_title('North/South Velocities at VENUS {node} on {date}'.format(
        node=station, date=timestamp.format('DD-MMM-YYYY')), **title_font)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    cbar.set_label('[m/s]', **axis_font)

    axw.invert_yaxis()
    mesh = axw.contourf(
        np.arange(0, 24, 0.25), dep_w[:],
        w_w[:, :, 1, 1].transpose(),
        np.arange(vmin/70, vmax/70, step/80),
        cmap=cmap)
    cbar = fig.colorbar(mesh, ax=axw)
    axw.set_ylim([dep_s, 0])
    axw.set_xlim([0, 23])
    axw.set_xlabel('Time [h]', **axis_font)
    axw.set_ylabel('Depth [m]', **axis_font)
    figures.axis_colors(axw, 'white')
    axw.set_title('Vertical Velocities at VENUS {node} on {date}'.format(
        node=station, date=timestamp.format('DD-MMM-YYYY')), **title_font)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    cbar.set_label('[m/s]', **axis_font)

    return fig


def VENUS_location(grid_B, figsize=(10, 10)):
    """Plots the location of the VENUS Central, East and DDL nodes as well as
    Vancouver as a reference on a bathymetry map.

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg figsize: Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    lats = grid_B.variables['nav_lat'][:]
    lons = grid_B.variables['nav_lon'][:]
    bathy = grid_B.variables['Bathymetry'][:]
    levels = np.arange(0, 470, 50)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.patch.set_facecolor('#2B3E50')
    cmap = plt.get_cmap('winter_r')
    cmap.set_bad('burlywood')
    mesh = ax.contourf(lons, lats, bathy, levels, cmap=cmap, extend='both')
    cbar = fig.colorbar(mesh)
    viz_tools.plot_land_mask(ax, grid_B, coords='map', color='burlywood')
    viz_tools.plot_coastline(ax, grid_B, coords='map')
    viz_tools.set_aspect(ax)

    lon_c = SITES['VENUS']['Central']['lon']
    lat_c = SITES['VENUS']['Central']['lat']
    lon_e = SITES['VENUS']['East']['lon']
    lat_e = SITES['VENUS']['East']['lat']
    lon_d = SITES['VENUS']['ddl']['lon']
    lat_d = SITES['VENUS']['ddl']['lat']
    lon_v = SITES['Vancouver']['lon']
    lat_v = SITES['Vancouver']['lat']

    ax.plot(
        lon_c,
        lat_c,
        marker='D',
        color='Black',
        markersize=10,
        markeredgewidth=2)
    bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.8)
    ax.annotate(
        'Central',
        (lon_c - 0.11, lat_c + 0.04),
        fontsize=15,
        color='black',
        bbox=bbox_args)

    ax.plot(
        lon_e,
        lat_e,
        marker='D',
        color='Black',
        markersize=10,
        markeredgewidth=2)
    bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.8)
    ax.annotate(
        'East',
        (lon_e + 0.04, lat_e + 0.01),
        fontsize=15,
        color='black',
        bbox=bbox_args)

    ax.plot(
        lon_d,
        lat_d,
        marker='D',
        color='Black',
        markersize=10,
        markeredgewidth=2)
    bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.8)
    ax.annotate(
        'DDL',
        (lon_d + 0.01, lat_d + 0.05),
        fontsize=15,
        color='black',
        bbox=bbox_args)

    ax.plot(
        lon_v,
        lat_v,
        marker='D',
        color='DarkMagenta',
        markersize=10,
        markeredgewidth=2)
    bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.8)
    ax.annotate(
        'Vancouver',
        (lon_v - 0.15, lat_v + 0.04),
        fontsize=15,
        color='black',
        bbox=bbox_args)

    ax.set_xlim([-124.02, -123.02])
    ax.set_ylim([48.5, 49.6])
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    figures.axis_colors(ax, 'white')
    ax.set_xlabel('Longitude', **axis_font)
    ax.set_ylabel('Latitude', **axis_font)
    ax.set_title('VENUS Node Locations', **title_font)
    cbar.set_label('Depth [m]', **axis_font)

    return fig


def load_vel(day, grid, source, station, deprange):
    """Prepares the model and observational velocities for plotting by
    unstaggering, masking and selecting the depths.
    :arg day: The day
    :type day: datetime object

    :arg grid: quarter-hourly results of the model at the VENUS nodes or
        half-hourly results of the VENUS ADCP values
    :type grid: dictionary or netCDF dataset

    :arg source: sets whether it is model values or observational values.
        'model' or 'observations'
    :type source: string

    :arg station: specifies the ONC VENUS nodes locations.
        'Central', 'East' or 'ddl'
    :type station: string

    :arg deprange: the range of depths that will be looked at in meters.
        (ex. [min, max])
    :type deprange: list
    """
    if source == 'model':
        # Set up model nowcast variables
        dep = grid.variables['depthv']
        jm = np.where(
            np.logical_and(dep[:] > deprange[0], dep[:] < deprange[1]))
        dep = dep[jm[0]]

        u_u = grid.variables['vozocrtx'][:, jm[0], :]
        v_v = grid.variables['vomecrty'][:, jm[0], :]
        u_E, v_N = unstag_rot(u_u, v_v)
        u_0 = u_E[..., 0, 0]
        v_0 = v_N[..., 0, 0]
        u = np.ma.masked_values(u_0, 0)
        v = np.ma.masked_values(v_0, 0)

    else:
        timemat = grid['mtime']
        # Find index in matlab datenum values that corresponds with the day of
        # interest.
        for mattime, count in zip(timemat[0], np.arange(len(timemat[0]))):
            time = (
                datetime.datetime.fromordinal(int(mattime)) +
                datetime.timedelta(days=mattime % 1) -
                datetime.timedelta(days=366))
            if time == day:
                # The -1 is because we access the 00:45:00 index which is the
                # second value of the day.
                ind = count-1

        # The obs values are every half hour. 48 values spans the whole day.
        oneday = 48
        dep = grid['chartdepth'][:][0]
        if np.logical_and(deprange[0] < 30, station == 'Central'):
            deprangeo = 30
        elif np.logical_and(deprange[0] < 20, station == 'East'):
            deprangeo = 20
        elif np.logical_and(deprange[0] < 15, station == 'ddl'):
            deprangeo = 15
        else:
            deprangeo = deprange[0]
        j = np.where(np.logical_and(dep[:] > deprangeo, dep[:] < deprange[1]))
        dep = dep[j[0]]
        # The velocities are in cm/s we want them in m/s.
        u0 = grid['utrue'][:][j[0], ind:ind+oneday]/100
        v0 = grid['vtrue'][:][j[0], ind:ind+oneday]/100

        u = np.ma.masked_invalid(u0)
        v = np.ma.masked_invalid(v0)

    return u, v, dep


def plotADCP(grid_m, grid_o, day, station, profile):
    """ This function will plots the velocities on a colour map with depth of the
    model and observational values.
    data over a whole day at a particular station.

    :arg grid_m: The model grid
    :type grid_m: neCDF4 dataset.

    :arg grid_o: The observational grid
    :type grid_o: dictionary

    :arg day: day of interest
    :type day: datetime object

    :arg station: Station of interest. Either 'Central' or 'East' or 'ddl'.
    :type station: string

    :arg profile: the range of depths that will be looked at in meters.
        (ex. [min, max])
    :type profile: list

    :return: fig
    """
    # Get grids into unstaggered and masked velocities at the chose depths
    u_E, v_N, dep_t = load_vel(day, grid_m, 'model', station, profile)
    u, v, dep = load_vel(day, grid_o, 'observation', station, profile)

    # Begin figure
    fig, ([axmu, axou], [axmv, axov]) = plt.subplots(
        2, 2,
        figsize=(20, 10),
        sharex=True)
    fig.patch.set_facecolor('#2B3E50')

    # Find the absolute maximum value between the model and observational
    # velocities to set the colorbar
    max_v = np.nanmax(abs(v))
    max_u = np.nanmax(abs(u))
    max_vm = np.nanmax(abs(v_N))
    max_um = np.nanmax(abs(u_E))
    max_speed = np.amax([max_v, max_u, max_vm, max_um])
    vmax = round(max_speed, 1)
    vmin = - vmax
    step = 0.05
    cs = np.arange(vmin, vmax + step, step)

    cmap = plt.get_cmap('bwr')

    # Setting the date for title
    date = day.strftime('%d%b%y')

    # Plotting the comparison between the model and the obs velocities
    increment = [0.25, 0.5, 0.25, 0.5]
    velocities = [u_E.transpose(), u, v_N.transpose(), v]
    axes = [axmu, axou, axmv, axov]
    depths = [dep_t, dep, dep_t, dep]
    names = ['Model', 'Observations', 'Model', 'Observations']
    direction = ['East/West', 'East/West', 'North/South', 'North/South']

    for ax, vel, timestep, depth, name, direc in zip(
            axes,
            velocities,
            increment,
            depths,
            names,
            direction):
        ax.invert_yaxis()
        mesh = ax.contourf(
            # The range below adjusts for the observations starting at 00:15
            # and being in 30 minutes increments.
            np.arange(timestep-0.25, 24+timestep-0.25, timestep),
            depth[:],
            vel,
            cs, cmap=cmap)
        ax.set_ylim([profile[1], profile[0]])
        ax.set_xlim([0.25, 23])
        ax.set_ylabel('Depth [m]', **axis_font)

        figures.axis_colors(ax, 'gray')
        ax.set_title(
            '{dire} {name} Velocities at VENUS {node} - {date}'.format(
                dire=direc, name=name, node=station, date=date), **title_font)

    cbar_ax = fig.add_axes([0.95, 0.2, 0.03, 0.6])
    cbar = fig.colorbar(mesh, cax=cbar_ax)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    cbar.set_label('[m/s]', **axis_font)
    axmv.set_xlabel('Hour [UTC]', **axis_font)
    axov.set_xlabel('Hour [UTC]', **axis_font)

    return fig


def plottimeavADCP(grid_m, grid_o, day, station):
    """ This function plots a comparison of the time averaged velocities of the
    model and the observations.

    :arg grid_m: The model grid
    :type grid_m: neCDF4 dataset.

    :arg grid_o: The observational grid
    :type grid_o: dictionary

    :arg day: day of interest
    :type day: datetime object

    :arg station: Station of interest. Either 'Central' or 'East' or 'ddl'
    :type station: string

    :return: fig
    """
    if station == 'Central':
        profile = [0, 290]
    elif station == 'East':
        profile = [0, 150]
    else:
        profile = [0, 150]

    # Get grids into unstaggered and masked velocities at the chose depths
    u_E, v_N, dep_t = load_vel(day, grid_m, 'model', station, profile)
    u, v, dep = load_vel(day, grid_o, 'observation', station, profile)

    # Begin figure
    fig, ([ax1, ax2]) = plt.subplots(1, 2, figsize=(8, 10), sharex=True)
    fig.patch.set_facecolor('#2B3E50')

    # Setting the date for title
    date = day.strftime('%d%b%y')

    velocities = [u_E[:, :-1], v_N[:, :-1]]
    vellast = [u_E[:, -2:], v_N[:, -2:]]
    veloobs = [u, v]
    axes = [ax1, ax2]
    direction = ['E/W', 'N/S']

    for ax, vel, velo, lastvel, direc in zip(
            axes, velocities, veloobs, vellast, direction):
        ax.plot(np.nanmean(vel, axis=0), dep_t[:-1],  label='Model')
        ax.plot(np.nanmean(velo, axis=1), dep[:], label='Observations')
        ax.plot(np.nanmean(
            lastvel, axis=0), dep_t[-2:], '--b', label='Bottom grid cell')
        ax.set_xlabel('Daily averaged velocity [m/s]', **axis_font)
        ax.set_ylabel('Depth [m]', **axis_font)
        figures.axis_colors(ax, 'gray')
        ax.set_title('{dire} velocities at VENUS {node}'.format(
            dire=direc, node=station, date=date), **title_font)
        ax.grid()
        ax.set_ylim(profile)
        ax.set_xlim([-0.5, 0.5])
        ax.invert_yaxis()
    ax1.legend(loc=0)

    return fig


def plotdepavADCP(grid_m, grid_o, day, station):
    """ This function plots a comparison of the depth averaged velocities of
    the model and the observations.

    :arg grid_m: The model grid
    :type grid_m: netCDF4 dataset.

    :arg grid_o: The observational grid
    :type grid_o: dictionary

    :arg day: day of interest
    :type day: datetime object

    :arg station: Station of interest. Either 'Central' or 'East' or 'ddl'
    :type station: string

    :return: fig
    """
    if station == 'Central':
        profile = [40, 270]
    elif station == 'East':
        profile = [30, 150]
    else:
        profile = [25, 130]

    # Get grids into unstaggered and masked velocities at the chose depths
    u_E, v_N, dep_t = load_vel(day, grid_m, 'model', station, profile)
    u, v, dep = load_vel(day, grid_o, 'observation', station, profile)

    # Depth averaging center of water column
    uE_av = analyze.depth_average(u_E, dep_t, 1)
    vN_av = analyze.depth_average(v_N, dep_t, 1)
    u_av = analyze.depth_average(u, dep[::-1], 0)
    v_av = analyze.depth_average(v, dep[::-1], 0)

    # Begin figure
    fig, ([ax1, ax2]) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    fig.patch.set_facecolor('#2B3E50')

    # Setting the date for title
    date = day.strftime('%d%b%y')

    timestep = 0.5
    velocities = [uE_av, vN_av]
    veloobs = [u_av, v_av]
    axes = [ax1, ax2]
    direction = ['East/West', 'North/South']

    for ax, vel, velo, direc in zip(axes, velocities, veloobs, direction):
        ax.plot(np.arange(0, 24, timestep/2), vel, label='Model')
        ax.plot(np.arange(0.25, 24, timestep), velo, label='Observations')
        ax.set_xlim([0, 24])
        ax.set_ylabel('Velocity [m/s]', **axis_font)
        figures.axis_colors(ax, 'gray')
        ax.set_title(
            'Depth Averaged ({}-{}m) {dire} velocities at VENUS {node} -{date}'
            .format(
                profile[0],
                profile[1],
                dire=direc,
                node=station,
                date=date),
            **title_font)
        ax.grid()
        ax.set_ylim([-0.6, 0.6])
    ax1.legend(loc=0)
    ax2.set_xlabel('Hour [UTC]')

    return fig


def plot_ellipses(
        params, x, y,
        depth='None',
        numellips=1,
        imin=0, imax=398,
        jmin=0, jmax=898):

    """ Plot ellipses on a map in the Salish Sea.
    :arg params: a array containing the parameters (possibly at different
        depths and or locations).The parameters must have 0 as major axis,
        1 as minor axis and 2 as inclination
    :type param: np.array

    :arg x: Horizontal index of the location at which the ellipse should be
        positioned. Should have equal or more values than numellips.
    :type x: float or np.array

    :arg y: Vertical index of the location at which the ellipse should be
        positioned. Should have equal or more values than numellips.
    :type y: float or np.array

    :arg depth: The depth at which you want to see the ellipse. If the param
         array has no depth dimensions put 'None'. Default 'None'.
    :arg depth: int

    :arg numellips: Number of ellipse that will be plotted from the params
        array. If =1 the function assumes there is no locations dimensions,
        only parameter and possibly depth if notified.
    :type numellips: int

    :arg imin: Minimum horizontal index that will be plotted.
    :type imin: int

    :arg imax: Maximum horizontal index that will be plotted.
    :type imax: int

    :arg jmin: Minimum vertical index that will be plotted.
    :type jmin: int

    :arg jmax: Maximum vertical index that will be plotted.
    :type jmax: int
    """
    phi = 0
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    k = np.zeros((898, 398))
    m = np.zeros((898, 398))
    scale = 10

    for q in np.arange(jmin, jmax):
        for l in np.arange(imin, imax):
            k[q, l] = q * np.cos(phi*np.pi/180.)+l*np.sin(phi*np.pi/180.)
            m[q, l] = -q * np.sin(phi*np.pi/180.)+l*np.cos(phi*np.pi/180.)

    if np.logical_and(numellips == 1, depth == 'None'):
        if params[1] > 0:
            thec = 'b'
        else:
            thec = 'r'
        ellsc1 = Ellipse(
            xy=(m[y, x], k[y, x]),
            width=scale * params[0],
            height=scale * params[1],
            angle=params[2]-29,
            color=thec)
        ax.add_artist(ellsc1)
        ellsc1.set_facecolor(thec)

    elif np.logical_and(numellips > 1, depth == 'None'):
        for r in np.arange(0, numellips):
            if params[r, 1] > 0:
                thec = 'b'
            else:
                thec = 'r'
            ellsc1 = Ellipse(
                xy=(m[y[r], x[r]], k[y[r], x[r]]),
                width=scale*params[r, 0],
                height=scale*params[r, 1],
                angle=params[r, 2]-29,
                color=thec)
            ax.add_artist(ellsc1)
            ellsc1.set_facecolor(thec)

    elif np.logical_and(numellips == 1, depth != 'None'):
            if params[depth, 2] > 0:
                thec = 'b'
            else:
                thec = 'r'
            ellsc1 = Ellipse(
                xy=(m[y, x], k[y, x]),
                width=scale*params[depth, 1],
                height=scale*params[depth, 2],
                angle=params[depth, 3]-29,
                color=thec)
            ax.add_artist(ellsc1)
            ellsc1.set_facecolor(thec)

    else:
        for r in np.arange(0, numellips):
            if params[r, depth, 2] > 0:
                thec = 'b'
            else:
                thec = 'r'
            ellsc1 = Ellipse(
                xy=(m[y[r], x[r]], k[y[r], x[r]]),
                width=scale*params[r, depth, 1],
                height=scale*params[r, depth, 2],
                angle=params[r, depth, 3]-29+phi,
                color=thec)
            ax.add_artist(ellsc1)
            ellsc1.set_facecolor(thec)

    grid_B = nc.Dataset(
        '/data/dlatorne/MEOPAR/NEMO-forcing/grid/bathy_meter_SalishSea2.nc')
    bathy = grid_B.variables['Bathymetry'][:, :]

    contour_interval = [-0.01, 0.01]
    ax.contourf(m[jmin:jmax, imin:imax],
                k[jmin:jmax, imin:imax],
                bathy.data[jmin:jmax, imin:imax],
                contour_interval,
                colors='black')
    ax.contour(m[jmin:jmax, imin:imax],
               k[jmin:jmax, imin:imax],
               bathy.data[jmin:jmax, imin:imax],
               [5],
               colors='black')
    ax.set_title('Tidal ellipse')
    ax.set_xlabel('x index')
    ax.set_ylabel('y index')
    print('red is clockwise')
    return


def plot_ellipses_area(
        params,
        depth='None',
        imin=0, imax=398,
        jmin=0, jmax=898,
        figsize=(10, 10)):

    """ Plot ellipses on a map in the Salish Sea.
    :arg params: a array containing the parameters (possibly at different
        depths and or locations).
    :type param: np.array

    :arg depth: The depth at which you want to see the ellipse. If the param
         array has no depth dimensions put 'None'. Default 'None'.
    :arg depth: int

    :arg imin: Minimum horizontal index that will be plotted.
    :type imin: int

    :arg imax: Maximum horizontal index that will be plotted.
    :type imax: int

    :arg jmin: Minimum vertical index that will be plotted.
    :type jmin: int

    :arg jmax: Maximum vertical index that will be plotted.
    :type jmax: int
    """
    phi = 0
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    k = np.zeros((898, 398))
    m = np.zeros((898, 398))
    scale = 10

    for q in np.arange(jmin, jmax):
        for l in np.arange(imin, imax):
            k[q, l] = q * np.cos(phi*np.pi/180.)+l*np.sin(phi*np.pi/180.)
            m[q, l] = -q * np.sin(phi*np.pi/180.)+l*np.cos(phi*np.pi/180.)

    if depth == 'None':
        for x in np.arange(imin, imax):
            for y in np.arange(jmin, jmax):
                if params[y, x, 1] > 0:
                    thec = 'b'
                else:
                    thec = 'r'
                ellsc = Ellipse(
                    xy=(m[y, x], k[y, x]),
                    width=scale * params[y, x, 0],
                    height=scale * params[y, x, 1],
                    angle=params[y, x, 2]-29,
                    color=thec)
                ax.add_artist(ellsc)

    else:
        for x in np.arange(imin, imax):
            for y in np.arange(jmin, jmax):
                if params[y, x, depth, 2] > 0:
                    thec = 'b'
                else:
                    thec = 'r'
                ellsc = Ellipse(
                    xy=(m[y, x], k[y, x]),
                    width=scale * params[y, x, depth, 1],
                    height=scale * params[y, x, depth, 2],
                    angle=params[y, x, depth, 3]-29,
                    color=thec)
                ax.add_artist(ellsc)

    grid_B = nc.Dataset(
        '/data/dlatorne/MEOPAR/NEMO-forcing/grid/bathy_meter_SalishSea2.nc')
    bathy = grid_B.variables['Bathymetry'][:, :]

    contour_interval = [-0.01, 0.01]
    ax.contourf(m[jmin:jmax, imin:imax],
                k[jmin:jmax, imin:imax],
                bathy.data[jmin:jmax, imin:imax],
                contour_interval,
                colors='black')
    ax.contour(m[jmin:jmax, imin:imax],
               k[jmin:jmax, imin:imax],
               bathy.data[jmin:jmax, imin:imax],
               [5],
               colors='black')
    ax.set_title('Tidal ellipse', fontsize=20)
    ax.set_xlabel('x index', fontsize=16)
    ax.set_ylabel('y index', fontsize=16)
    print('red is clockwise')
    return fig
