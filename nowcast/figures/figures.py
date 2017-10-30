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

"""A collection of Python functions to produce model results visualization
figures for analysis and model evaluation of daily nowcast/forecast runs.

.. warning::
    This module will soon disappear.
    It is in the process of being refactored into a new
    one-module-per-figure architecture.
    **Please do not add code to this module.**
    If you are importing this module to use functions from it,
    please create an issue at https://bitbucket.org/salishsea/tools/issues
    that describes the function you are using and your use-case.
    Such functions will be moved into the :ref:`SalishSeaToolsPackage`.
"""
import datetime
import glob
import io
import os

import matplotlib.cm as cm
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
import pandas as pd
import requests
from dateutil import tz
from matplotlib.backends import backend_agg as backend
from salishsea_tools import (
    geo_tools,
    nc_tools,
    stormtools,
    tidetools,
    viz_tools,
)
from scipy import interpolate as interp

from nowcast.figures import shared
# =============================== #
# <------- Kyle 2015/08/25
ms2k = 1/0.514444
k2ms = 0.514444
# conversion between m/s and knots
# =============================== #

# Plotting colors
model_c = 'MediumBlue'
observations_c = 'DarkGreen'
predictions_c = 'MediumVioletRed'
stations_c = cm.rainbow(np.linspace(0, 1, 7))
SITE_BACKGROUND_COLOUR = '#2B3E50'  # salishsea site Superhero theme background
COLOURS = {
    'figure': {
        'facecolor': SITE_BACKGROUND_COLOUR,
        'location label': 'DimGray',
    },
    'axis': {
        'labels': 'white',
        'spines': 'white',
        'ticks': 'white',
        'title': 'white',
    },
    'cbar': {
        'label': 'white',
        'tick labels': 'white',
    },
    'wind arrow': {
        'facecolor': 'DarkMagenta',
        'edgecolor': 'black',
    },
    'risk level colours': {
        'extreme risk': 'red',
        'moderate risk': 'Gold',
        None: 'green',
    },
}
# Time shift for plotting in PST
time_shift = datetime.timedelta(hours=-8)
hfmt = mdates.DateFormatter('%m/%d %H:%M')

# Font format
title_font = {
    'fontname': 'Bitstream Vera Sans', 'size': '15', 'color': 'black',
    'weight': 'medium'
}
axis_font = {'fontname': 'Bitstream Vera Sans', 'size': '13'}
FONTS = {
    'website_thumbnail_title': {
        'fontname': 'Bitstream Vera Sans',
        'size': '40',
        'color': 'white',
        'weight': 'medium',
    }
}

# Constant with station information: mean sea level, latitude,
# longitude, station number, historical extreme ssh, etc.
# Extreme ssh from DFO website
# Mean sea level from CHS tidal constiuents.
# VENUS coordinates from the VENUS website. Depth is in meters.

SITES = {
    'Nanaimo': {
        'lat': 49.16,
        'lon': -123.93,
        'msl': 3.08,
        'extreme_ssh': 5.47},
    'Halibut Bank': {
        'lat': 49.34,
        'lon': -123.72},
    'Dungeness': {
        'lat': 48.15,
        'lon': -123.117},
    'La Perouse Bank': {
        'lat': 48.83,
        'lon': -126.0},
    'Point Atkinson': {
        'lat': 49.33,
        'lon': -123.25,
        'msl': 3.09,
        'stn_no': 7795,
        'extreme_ssh': 5.61},
    'Victoria': {
        'lat': 48.41,
        'lon': -123.36,
        'msl': 1.8810,
        'stn_no': 7120,
        'extreme_ssh': 3.76},
    'Campbell River': {
        'lat': 50.04,
        'lon': -125.24,
        'msl': 2.916,
        'stn_no': 8074,
        'extreme_ssh': 5.35},
    'Neah Bay': {
        'lat': 48.4,
        'lon': -124.6,
        'stn_no':  9443090},
    'Friday Harbor': {
        'lat': 48.55,
        'lon': -123.016667,
        'stn_no': 9449880},
    'Cherry Point': {
        'lat': 48.866667,
        'lon': -122.766667,
        'stn_no': 9449424,
        'msl': 3.543,
        'extreme_ssh': 5.846},
    'SandHeads': {
        'lat': 49.10,
        'lon': -123.30},
    'Tofino': {
        'lat': 49.15,
        'lon': -125.91,
        'stn_no': 8615},
    'Bamfield': {
        'lat': 48.84,
        'lon': -125.14,
        'stn_no': 8545},
    'VENUS': {
        'East': {
            'lat': 49.0419,
            'lon': -123.3176,
            'depth': 170},
        'Central': {
            'lat': 49.0401,
            'lon': -123.4261,
            'depth': 300}
        }
    }

# Sites for producing water level thresold plots
TIDAL_SITES = ['Point Atkinson', 'Victoria', 'Campbell River', 'Nanaimo',
               'Cherry Point']


def save_image(fig, filename, **kwargs):
    """Save fig as an image file in filename.

    :arg fig: Figure object to save as image file.
    :type fig: :class:`matplotlib.Figure`

    :arg filename: File path/name to save fig object to.
                   The filename extension specifies the type of image
                   file to create;
                   e.g. .png, .svg, etc.
    :type filename: str

    :arg kwargs: Keyword argument names and values to control how fig
                 is rendered;
                 e.g. :kbd:`facecolor=fig.get_facecolor()`,
                 :kbd:`bbox_inches='tight'`, etc.
                 See the matplotlib docs for details.
    :type kwargs: dict
    """
    canvas = backend.FigureCanvasAgg(fig)
    canvas.print_figure(filename, **kwargs)


def axis_colors(ax, plot):
    """Formats the background colour of plots and colours of labels.

    :arg ax: Axis to be formatted.
    :type ax: axis object

    :arg plot: Keyword for background needed for plot.
    :type plot: string

    :returns: axis format
    """

    labels_c = 'white'
    ticks_c = 'white'
    spines_c = 'white'

    if plot == 'blue':
        ax.set_axis_bgcolor('#2B3E50')
    if plot == 'gray':
        ax.set_axis_bgcolor('#DBDEE1')
    if plot == 'white':
        ax.set_axis_bgcolor('white')

    ax.xaxis.label.set_color(labels_c), ax.yaxis.label.set_color(labels_c)
    ax.tick_params(axis='x', colors=ticks_c)
    ax.tick_params(axis='y', colors=ticks_c)
    ax.spines['bottom'].set_color(spines_c)
    ax.spines['top'].set_color(spines_c)
    ax.spines['left'].set_color(spines_c)
    ax.spines['right'].set_color(spines_c)
    ax.title.set_color('white')

    return ax


def interpolate_depth(data, depth_array, depth_new):
    """Interpolates data field to a desired depth.

    :arg data: The data to be interpolated.
               Should be one-dimensional over the z-axis.
    :type data: 1-d numpy array

    :arg depth_array: The z-axis for data.
    :type depth_array: 1-d numpy array

    :arg depth_new: The new depth to which we want to interpolate.
    :type depth_new: float

    :returns: float representing the field interpolated to the desired depth
              (data_interp).
    """

    # Masked arrays are used for more accurate interpolation.
    mu = data == 0
    datao = np.ma.array(data, mask=mu)
    mu = depth_array == 0
    depth_arrayo = np.ma.array(depth_array, mask=mu)

    # Interpolations
    f = interp.interp1d(depth_arrayo, datao)
    data_interp = f(depth_new)

    return data_interp


def get_model_time_variables(grid_T):
    """Return start time, end time, and the time counter values from a
    NEMO tracer results dataset.

    :arg grid_T: Tracer results dataset from NEMO.
    :type grid_T: :py:class:`netCDF4.Dataset`

    :returns: dataset start time, dataset end time,
              and array of output times all as datetime objects.
    """
    time = nc_tools.timestamp(
        grid_T, range(grid_T.variables['time_counter'].size))
    time = np.array([t.datetime for t in time])
    return time[0], time[-1], time


def dateparse_PAObs(s1, s2, s3, s4):
    """Parse dates for Point Atkinson observations."""

    s = s1 + s2 + s3 + s4
    unaware = datetime.datetime.strptime(s, '%Y%m%d%H:%M')
    aware = unaware.replace(tzinfo=tz.tzutc())

    return aware


def dateparse_archive_obs(s):
    """Function to make datetime object aware of time zone
    e.g. date_parser=dateParserMeasured('2014/05/31 11:42')

    :arg s: string of date and time
    :type s: str

    :returns: datetime object that is timezone aware
    """
    PST_tz = tz.tzoffset("PST", -28800)
    # Convert the string to a datetime object
    unaware = datetime.datetime.strptime(s, "%Y/%m/%d %H:%M")
    # Add in the local time zone (Canada/Pacific)
    aware = unaware.replace(tzinfo=PST_tz)
    # Convert to UTC
    return aware.astimezone(tz.tzutc())


def load_archived_observations(name, start_date, end_date):
    """
    Loads tidal observations from the DFO archive website.
    Note: only archived observations can be loaded. This usually means
    at least one month old. If data is not available, a DataFrame with
    one NaN recording is returned.

    :arg name: a string representing the location for observations
    :type name: a string from the following - Point Atkinson, Victoria,
     Campbell River

    :arg start_date: a string representing the starting date of the
     observations.
    :type start_date: string in format %d-%b-%Y

    :arg end: a string representing the end date of the observations.
    :type end: string in format %d-%b-%Y

    :returns: wlev_meas: a dict object with the water level measurements
     reference to Chart Datum. Columns are time and wlev. Time is in UTC.
    """

    station_no = SITES[name]['stn_no']
    base_url = 'http://www.meds-sdmm.dfo-mpo.gc.ca/isdm-gdsi/twl-mne/inventory-inventaire/'
    form_handler = (
        'data-donnees-eng.asp?user=isdm-gdsi&region=PAC&tst=1&no='
        + str(station_no))
    sitedata = {
        'start_period': start_date,
        'end_period': end_date,
        'resolution': 'h',
        'time_zone': 'l',
    }
    data_provider = (
        'download-telecharger.asp'
        '?File=E:%5Ciusr_tmpfiles%5CTWL%5C'
        + str(station_no) + '-'+start_date + '_slev.csv'
        '&Name=' + str(station_no) + '-'+start_date+'_slev.csv')
    # Go get the data from the DFO site
    with requests.Session() as s:
        s.post(base_url + form_handler, data=sitedata)
        r = s.get(base_url + data_provider)
    # Write the data to a fake file
    fakefile = io.StringIO(r.text)
    # Read the fake file
    try:
        wlev_meas = pd.read_csv(
            fakefile, skiprows=7, parse_dates=[0],
            date_parser=dateparse_archive_obs)
    except pd.parser.CParserError:
        data = {'Obs_date': datetime.datetime.strptime(start_date, '%d-%b-%Y'),
                'SLEV(metres)': float('NaN')}
        wlev_meas = pd.DataFrame(data=data, index=[0])

    wlev_meas = wlev_meas.rename(
        columns={'Obs_date': 'time', 'SLEV(metres)': 'wlev'})

    return wlev_meas


def load_PA_observations():
    """Loads the recent water level observations at Point Atkinson.

    Times are in UTC and water level is in metres with respect to Chart Datum.

    :returns: DataFrame object (obs) with a time column and wlev column.
    """

    filename = (
        '/data/nsoontie/MEOPAR/analysis/Nancy/tides/PA_observations/'
        'ptatkin_rt.dat')

    obs = pd.read_csv(
        filename, delimiter=' ', parse_dates=[[0, 1, 2, 3]], header=None,
        date_parser=dateparse_PAObs)
    obs = obs.rename(columns={'0_1_2_3': 'time', 4: 'wlev'})

    return obs


def get_maxes(ssh, t, res, lon, lat, weather_path):
    """Identifies maximum ssh and other important features such as the
    timing, residual, and wind speed.

    :arg ssh: The ssh field to be maximized.
    :type ssh: numpy array

    :arg t: The times corresponding to the ssh.
    :type t: numpy array

    :arg res: The residual.
    :type res: numpy array

    :arg float lon: The longitude of the station for looking up wind.

    :arg float lat: The latitude of the station for looking up wind.

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :returns: maxmimum ssh (max_ssh), index of maximum ssh (index_ssh),
              time of maximum ssh (tmax), residual at that time (max_res),
              wind speed at that time (max_wind),
              and the index of that wind speed (ind_w).
    """

    # Index when sea surface height is at its maximum at Point Atkinson
    max_ssh = np.max(ssh)
    index_ssh = np.argmax(ssh)
    tmax = t[index_ssh]
    max_res = res[index_ssh]

    # Get model winds
    t_orig = t[0]
    t_final = t[-1]
    [wind, direc, t_wind, pr, tem, sol, the, qr, pre] = get_model_winds(
        lon, lat, t_orig, t_final, weather_path)
    # Index where t_wind=tmax
    # (Find a match between the year, month, day and hour)
    ind_w = np.where(
        t_wind == datetime.datetime(
            tmax.year, tmax.month, tmax.day, tmax.hour))[0]
    max_wind = wind[ind_w]

    return max_ssh, index_ssh, tmax, max_res, max_wind, ind_w


def get_weather_filenames(t_orig, t_final, weather_path):
    """Gathers a list of "Operational" atmospheric model filenames in a
    specifed date range.

    :arg datetime t_orig: The beginning of the date range of interest.

    :arg datetime t_final: The end of the date range of interest.

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :returns: list of files names (files) from the Operational model.
    """
    numdays = (t_final - t_orig).days
    dates = [
        t_orig + datetime.timedelta(days=num)
        for num in range(0, numdays + 1)]
    dates.sort()

    allfiles = glob.glob(os.path.join(weather_path, 'ops_y*'))
    sstr = os.path.join(weather_path, dates[0].strftime('ops_y%Ym%md%d.nc'))
    estr = os.path.join(weather_path, dates[-1].strftime('ops_y%Ym%md%d.nc'))
    files = []
    for filename in allfiles:
        if filename >= sstr:
            if filename <= estr:
                files.append(filename)
    files.sort(key=os.path.basename)

    return files


def get_model_winds(lon, lat, t_orig, t_final, weather_path):
    """Returns meteorological fields for the "Operational" model at a given
    longitude and latitude over a date range.

    :arg float lon: The specified longitude.

    :arg float lat: The specified latitude.

    :arg datetime t_orig: The beginning of the date range of interest.

    :arg datetime t_final: The end of the date range of interest.

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :returns: wind speed (wind), wind direction (direc), time (t),
              pressure (pr), temperature (tem), solar radiation (sol),
              thermal radiation (the),humidity (qr), precipitation (pre).
    """

    # Weather file names
    files = get_weather_filenames(t_orig, t_final, weather_path)
    weather = nc.Dataset(files[0])
    Y = weather.variables['nav_lat'][:]
    X = weather.variables['nav_lon'][:] - 360

    [j, i] = geo_tools.find_closest_model_point(lon, lat, X, Y, grid="GEM2.5")

    wind = np.array([])
    direc = np.array([], 'double')
    t = np.array([])
    pr = np.array([])
    sol = np.array([])
    the = np.array([])
    pre = np.array([])
    tem = np.array([])
    qr = np.array([])
    for f in files:
        G = nc.Dataset(f)
        u = G.variables['u_wind'][:, j, i]
        v = G.variables['v_wind'][:, j, i]
        pr = np.append(pr, G.variables['atmpres'][:, j, i])
        sol = np.append(sol, G.variables['solar'][:, j, i])
        qr = np.append(qr, G.variables['qair'][:, j, i])
        the = np.append(the, G.variables['therm_rad'][:, j, i])
        pre = np.append(pre, G.variables['precip'][:, j, i])
        tem = np.append(tem, G.variables['tair'][:, j, i])
        speed = np.sqrt(u ** 2 + v ** 2)
        wind = np.append(wind, speed)

        d = np.arctan2(v, u)
        d = np.rad2deg(d + (d < 0) * 2 * np.pi)
        direc = np.append(direc, d)

        ts = G.variables['time_counter']
        # There is no time_origin attribute in OP files; this is hard coded.
        torig = datetime.datetime(1970, 1, 1)
        for ind in np.arange(ts.shape[0]):
            t = np.append(t, torig + datetime.timedelta(seconds=ts[ind]))
    return wind, direc, t, pr, tem, sol, the, qr, pre


def load_model_ssh(grid_T):
    """Load an sea surface height (ssh) time series from a NEMO tracer
    results dataset.

    :arg grid_T: Tracer results dataset from NEMO.
    :type grid_T: :py:class:`netCDF4.Dataset`

    :returns: ssh, time - the ssh and time arrays
    :rtype: 2-tuple of :py:class:`numpy.ndarray`
    """
    ssh = grid_T.variables['sossheig'][:, 0, 0]
    t_orig, t_final, time = get_model_time_variables(grid_T)
    return ssh, time


## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as sandheads_winds
def SandHeads_winds(
        grid_T, grid_B, weather_path, coastline, PST=1, figsize=(20, 12)):
    """Plots the observed and modelled winds at Sand Heads during the
    simulation.

    Observations are from Environment Canada data:
    http://climate.weather.gc.ca/
    Modelled winds are the HRDPS nested model from Environment Canada.

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg PST: Specifies if plot should be presented in PST.
              1 = plot in PST, 0 = plot in UTC.
    :type PST: 0 or 1

    :arg figsize:  Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    # Time range
    t_orig, t_end, t_nemo = get_model_time_variables(grid_T)
    timezone = PST * '[PST]' + abs((PST - 1)) * '[UTC]'

    # Strings for timetamps of EC data
    start = t_orig.strftime('%d-%b-%Y')
    end = t_end.strftime('%d-%b-%Y')

    winds, dirs, temps, time, lat, lon = stormtools.get_EC_observations(
        'Sandheads', start, end)
    time = np.array(time)
    wind_ax = np.array([0, 20])  # axis limits in m/s

    # Get modelled winds
    wind, direc, t, pr, tem, sol, the, qr, pre = get_model_winds(
        lon, lat, t_orig, t_end, weather_path)
    gs = gridspec.GridSpec(2, 2, width_ratios=[1.5, 1])
    gs.update(wspace=0.13, hspace=0.2)

    # Figure
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor('#2B3E50')
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0])
    ax0 = fig.add_subplot(gs[:, 1])
    ax12 = ax1.twinx()  # axis for knots wind plotting

    # Plot wind speed
    ax1.plot(
        time + PST * time_shift, winds,
        color=observations_c, lw=2, label='Observations')
    ax1.plot(t + PST * time_shift, wind, lw=2, color=model_c, label='Model')
    ax1.set_xlim([t_orig + PST * time_shift, t_end + PST * time_shift])
    ax1.set_ylim(wind_ax)
    ax1.set_title('Winds at Sand Heads:  ' + start, **title_font)
    ax1.set_ylabel('Wind Speed (m/s)', **axis_font)
    ax1.set_xlabel('Time {}'.format(timezone), **axis_font)
    ax1.legend(loc=0)
    # =================================================== #
    # <----------------------- Kyle 2015/08/25
    # axis for knots plotting
    ax12.set_ylim(wind_ax*ms2k)
    ax12.set_ylabel('Wind Speed (knots)', **axis_font)
    axis_colors(ax12, 'gray')
    # =================================================== #
    axis_colors(ax1, 'gray')
    ax1.xaxis.set_major_formatter(hfmt)
    ax1.grid()

    # Plot wind direction
    ax2.plot(
        time + PST * time_shift, dirs,
        lw=2, color=observations_c, label='Observations')
    ax2.plot(t + PST * time_shift, direc, lw=2, color=model_c, label='Model')
    ax2.set_xlim([t_orig + PST * time_shift, t_end + PST * time_shift])
    ax2.set_ylim([0, 360])
    ax2.set_xlabel(
        'Time ' + PST * '[PST]' + abs((PST - 1)) * '[UTC]', **axis_font)
    ax2.set_ylabel('Wind To Direction \n (degrees CCW of East)', **axis_font)
    ax2.legend(loc=0)
    ax2.grid()
    axis_colors(ax2, 'gray')
    ax2.xaxis.set_major_formatter(hfmt)
    fig.autofmt_xdate()
    # Fix ticks on speed plot
    ax1.set_xticks(ax2.get_xticks())

    # Map
    _plot_stations_map(ax0, coastline, title='Station Locations')

    ax0.plot(
        lon, lat,
        marker='D', markersize=10, markeredgewidth=2,
        color='DarkMagenta')
    bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.8)
    ax0.annotate(
        'Sand Heads', (lon - 0.05, lat - 0.15),
        fontsize=15, color='black', bbox=bbox_args)

    # Citation
    ax0.text(0.0, -0.15,
             'Observations from Environment Canada data. '
             'http://climate.weather.gc.ca/ \n'
             'Modelled winds are from the High Resolution Deterministic '
             'Prediction System\n'
             'of Environment Canada.\n'
             'https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html',
             horizontalalignment='left',
             verticalalignment='top',
             transform=ax0.transAxes, color='white')

    return fig


def ssh_PtAtkinson(grid_T, grid_B=None, figsize=(20, 5)):
    """Plots hourly sea surface height at Point Atkinson.

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg figsize: Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    ssh = grid_T.variables['sossheig']
    results_date = nc_tools.timestamp(grid_T, 0).format('YYYY-MM-DD')
    ax.plot(ssh[:, 468, 328], 'o')
    ax.set_title(
        'Hourly Sea Surface Height at Point Atkinson on {}'
        .format(results_date))
    ax.set_xlabel('UTC Hour from {}'.format(results_date))
    ax.set_ylabel(
        '{label} [{units}]'
        .format(label=ssh.long_name.title(), units=ssh.units))
    ax.grid()

    return fig


def _plot_stations_map(
    ax, coastline, title, xlim=(-125.4, -122.2), ylim=(48, 50.3)
):
    """Plots map of Salish Sea region, including the options to add a
    coastline

    :arg ax: Axis for map.
    :type ax: axis object

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    :arg title: An informative title for the axis
    :type title: string

    :arg xlim: limits of the x-axis
    :type xlim: 2-tuple

    :arg ylim: limits of the y-axis
    :type ylim: 2-tuple
    """

    shared.plot_map(ax, coastline, lon_range=xlim, lat_range=ylim)
    ax.set_xlabel('Longitude', **axis_font)
    ax.set_ylabel('Latitude', **axis_font)
    ax.grid()
    viz_tools.set_aspect(ax)
    ax.set_title(title, **title_font)
    axis_colors(ax, 'gray')
