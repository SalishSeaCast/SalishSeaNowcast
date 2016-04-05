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


"""A collection of Python functions to produce model results visualization
figures for analysis and model evaluation of daily nowcast/forecast runs.
"""
import datetime
import glob
import io
import os

import arrow
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
from scipy import interpolate as interp

from salishsea_tools import (
    nc_tools,
    stormtools,
    tidetools,
    unit_conversions,
    viz_tools,
    wind_tools,
)
from salishsea_tools.places import PLACES

from nowcast.figures import (
    shared,
    website_theme,
)


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
    'Sandheads': {
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
# Sites for adding wind vectors to map
WIND_SITES = ['La Perouse Bank', 'Neah Bay', 'Dungeness', 'Victoria',
              'Friday Harbor', 'Cherry Point', 'Sandheads',
              'Point Atkinson', 'Halibut Bank', 'Nanaimo', 'Campbell River']
# Colors for wind stations
stations_c = cm.rainbow(np.linspace(0, 1, len(WIND_SITES)))


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


def find_model_point(lon, lat, X, Y, tol_lon=0.016, tol_lat=0.011):
    """Finds a model grid point close to a specified latitude and longitude.
    Should be used for non-NEMO grids like the atmospheric forcing grid.

    :arg lon: The longitude we are trying to match.
    :type lon: float

    :arg lat: The latitude we are trying to match.
    :type lat: float

    :arg X: The model longitude grid.
    :type X: numpy array

    :arg Y: The model latitude grid.
    :type Y: numpy array

    :arg tol_lon: tolerance on grid spacing for longitude
    :type tol_lon: float

    :arg tol_lat: tolerance on grid spacing for latitude
    :type tol_lat: float

    :returns: j-index and i-index of the closest model grid point.
    """

    # Search for a grid point with longitude or latitude within
    # tolerance of measured location
    j, i = np.where(
        np.logical_and(
            (np.logical_and(X > lon - tol_lon, X < lon + tol_lon)),
            (np.logical_and(Y > lat - tol_lat, Y < lat + tol_lat))))

    if j.size > 1 or i.size > 1:
        raise ValueError(
            'Multiple model points found. tol_lon/tol_lat too big.'
        )
    elif not j or not i:
        raise ValueError(
            'No model point found. tol_lon/tol_lat too small or '
            'lon/lat outside of domain.'
        )
    return j, i


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


def dateparse_NOAA(s):
    """Parse the dates from the NOAA files."""

    unaware = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M')
    aware = unaware.replace(tzinfo=tz.tzutc())

    return aware


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


def get_NOAA_wlevels(station_no, start_date, end_date, product='water_level'):
    """Retrieves recent NOAA water levels from a station in a given date range.

    NOAA water levels are at 6 minute intervals and are relative to
    mean sea level.
    See: http://tidesandcurrents.noaa.gov/stations.html?type=Water+Levels.

    :arg station_no: NOAA station number.
    :type station_no: int

    :arg start_date: The start of the date range; e.g. 01-Jan-2014.
    :type start_date: str

    :arg end_date: The end of the date range; e.g. 02-Jan-2014.
    :type end_date: str

    :arg product: Defines which NOAA product to use. Options are 'water_level'
                  for recent data, 'hourly_height' for archived
    :type product: str

    :returns: DataFrame object (obs) with time and wlev columns,
              among others that are irrelevant.
    """

    # Time range
    st_ar = arrow.Arrow.strptime(start_date, '%d-%b-%Y')
    end_ar = arrow.Arrow.strptime(end_date, '%d-%b-%Y')

    base_url = (
        'http://tidesandcurrents.noaa.gov/api/datagetter'
        '?product={}&application=NOS.COOPS.TAC.WL'.format(product))
    params = {
        'begin_date': st_ar.format('YYYYMMDD'),
        'end_date': end_ar.format('YYYYMMDD'),
        'datum': 'MSL',
        'station': str(station_no),
        'time_zone': 'GMT',
        'units': 'metric',
        'format': 'csv',
    }
    response = requests.get(base_url, params=params)

    fakefile = io.StringIO(response.text)
    try:
        obs = pd.read_csv(
            fakefile, parse_dates=[0], date_parser=dateparse_NOAA)
    except ValueError:
        data = {'Date Time': st_ar.datetime, ' Water Level': float('NaN')}
        obs = pd.DataFrame(data=data, index=[0])
    obs = obs.rename(columns={'Date Time': 'time', ' Water Level': 'wlev'})
    return obs


def get_NOAA_tides(station_no, start_date, end_date, interval=''):
    """Retrieves NOAA predicted tides from a station in a given date range.

    NOAA predicted tides are at 6-minute intervals and are relative to
    mean sea level. See:
    http://tidesandcurrents.noaa.gov/stations.html?type=Water+Levels.

    :arg station_no: NOAA station number.
    :type station_no: integer

    :arg start_date: The start of the date range eg. 01-Jan-2014.
    :type start_date: string

    :arg end_date: The end of the date range eg. 02-Jan-2014.
    :type end_date: string

    :arg interval: Interval for tide record. Default is '', meaning highest
                   frequency available. 'h' corresponds to hourly.
    :type interval: string

    :returns: DataFrame object (tides) with time and pred columns.
    """

    # Time range
    st_ar = arrow.Arrow.strptime(start_date, '%d-%b-%Y')
    end_ar = arrow.Arrow.strptime(end_date, '%d-%b-%Y')

    base_url = (
        'http://tidesandcurrents.noaa.gov/api/datagetter'
        '?product=predictions&application=NOS.COOPS.TAC.WL')
    params = {
        'begin_date': st_ar.format('YYYYMMDD'),
        'end_date': end_ar.format('YYYYMMDD'),
        'datum': 'MSL',
        'station': str(station_no),
        'time_zone': 'GMT',
        'units': 'metric',
        'interval': interval,
        'format': 'csv',
    }

    response = requests.get(base_url, params=params)

    fakefile = io.StringIO(response.text)
    try:
        tides = pd.read_csv(
            fakefile, parse_dates=[0], date_parser=dateparse_NOAA)
    except ValueError:
        data = {'Date Time': st_ar.datetime, ' Prediction': float('NaN')}
        tides = pd.DataFrame(data=data, index=[0])
    tides = tides.rename(columns={'Date Time': 'time', ' Prediction': 'pred'})
    return tides


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


def compute_residual(ssh, t_model, ttide):
    """Compute the difference between modelled ssh and tidal predictions for a
    range of dates.

    Both modelled ssh and tidal predictions use eight tidal constituents.

    :arg ssh: The modelled ssh (without corrections).
    :type ssh: numpy array

    :arg t_model: model output times
    :type t_model: array of datetime objects

    :arg ttide: The tidal predictions.
    :type ttide: DateFrame object with columns time, pred_all and pred_8

    :returns: numpy array for residual (res).
    """

    # interpolate tides to model time
    tides_interp = shared.interp_to_model_time(t_model, ttide.pred_all, ttide.time)

    res = ssh - tides_interp

    return res


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

    [j, i] = find_model_point(lon, lat, X, Y)

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


def plot_corrected_model(
        ax, t, ssh_loc, ttide, PST, MSL, msl):
    """Plots and returns corrected model.

    The model is corrected for the tidal constituents that are not included
    in the model forcing.

    :arg ax: The axis where the corrected model is plotted.
    :type ax: axis object

    :arg t: The time of model output.
    :type t: numpy array

    :arg ssh_loc: The model sea surface height to be corrected (1 dimensional).
    :type ssh_loc: numpy array

    :arg ttide: The tidal predictions with columns time, pred_all, pred_8.
    :type ttide: DataFrame object

    :arg PST: Specifies if plot should be presented in PST.
              1 = plot in PST, 0 = plot in UTC.
    :type PST: 0 or 1

    :arg MSL: Specifies if the plot should be centred about mean sea level.
              1=centre about MSL, 0=centre about 0.
    :type MSL: 0 or 1

    :arg msl: The mean sea level for centring the plot.
    :type msl: float

    :returns: corrected model output (ssh_corr).
    """

    # Correct the ssh
    ssh_corr = shared.correct_model_ssh(ssh_loc, t, ttide)

    ax.plot(
        t + PST * time_shift,
        ssh_corr + msl * MSL,
        '-', c=model_c, linewidth=2, label='Corrected model')

    return ssh_corr


def plot_tides(ax, name, PST, MSL, tidal_predictions, color=predictions_c):
    """Plots and returns the tidal predictions at a given station during the
    year of t_orig.

    This function is only for Victoria, Campbell River, Point Atkinson
    and Patricia Bay.
    Tidal predictions are stored in a specific location.

    :arg ax: The axis where the tides are plotted.
    :type ax: axis object

    :arg str name: The name of the station.

    :arg int PST: Specifies if plot should be presented in PST.
                  1 = plot in PST, 0 = plot in UTC.

    :arg int MSL: Specifies if the plot should be centred about mean sea level.
                  1=centre about MSL, 0=centre about 0.

    :arg str tidal_predictions: Path to directory of tidal prediction
                                 file.

    :arg str color: The color for the tidal predictions plot.

    :returns: DataFrame object (ttide) with tidal predictions and
              columns time, pred_all, pred_8.
    """

    ttide = shared.get_tides(name, tidal_predictions)
    ax.plot(
        ttide.time + PST * time_shift,
        ttide.pred_all + SITES[name]['msl'] * MSL,
        c=color, linewidth=2, label='Tidal predictions')

    return ttide


def plot_PA_observations(ax, PST):
    """Plots the water level observations at Point Atkinson.

    :arg ax: The axis where the PA observations are plotted.
    :type ax: axis object

    :arg PST: Specifies if plot should be presented in PST.
              1 = plot in PST, 0 = plot in UTC.
    :type PST: 0 or 1
    """

    obs = load_PA_observations()
    ax.plot(
        obs.time + PST * time_shift,
        obs.wlev,
        color=observations_c, lw=2, label='Observations')


def plot_risk_level_marker(
    ax, name, risk_level, colours, marker, msize, alpha,
):
    ax.plot(
        *PLACES[name]['lon lat'],
        marker=marker, markersize=msize, markeredgewidth=2,
        color=colours['risk level colours'][risk_level], alpha=alpha)


def plot_threshold_map(ax, ttide, ssh_corr, marker, msize, alpha, name):
    """Determines category (green, yellow, red) in which the max sea surface
    height at a station falls.
    """
    # Easy access to several constants
    lat = SITES[name]['lat']
    lon = SITES[name]['lon']
    msl = SITES[name]['msl']
    extreme_ssh = SITES[name]['extreme_ssh']

    # Determine thresholds
    max_tides = max(ttide.pred_all) + msl
    mid_tides = 0.5 * (extreme_ssh - max_tides) + max_tides
    max_ssh = np.max(ssh_corr) + msl

    # Threshold colors
    if max_ssh < (max_tides):
        threshold_c = 'green'
    elif max_ssh > (mid_tides):
        threshold_c = 'red'
    else:
        threshold_c = 'Gold'

    ax.plot(
        lon, lat,
        marker=marker, markersize=msize, markeredgewidth=2,
        color=threshold_c, alpha=alpha)

    return max_tides, mid_tides, extreme_ssh


def plot_wind_vector(ax, name, t_orig, t_final, weather_path, inds, scale):
    """ Plots a single wind vector at a station in an axis.

    Winds are averaged over the times represented by the indices in
    inds[0] and inds[-1].

    :arg ax: The axis for plotting.
    :type ax: an axis object

    :arg str name: The name of the station, can be Neah Bay, Point Atkinson,
                   Campbell River, Victoria, Friday Harbor, Cherry Point,
                   Sandheads.

    :arg datetime t_orig: start time of the simulation.

    :arg datetime t_final: end time fo simulation.

    :arg str weather_path: Path to the weather forcing files.

    :arg inds: indices corresponding to the time range of desired wind plots.
               If inds='all', the average will span the entire simulation.
    :type inds: numpy array, or string 'all'

    :arg float scale: scale of arrows for plotting wind vector.

    :returns: tplot, an array with the time range winds were averaged:
              tplot[0] and tplot[-1] .
    """
    lat = SITES[name]['lat']
    lon = SITES[name]['lon']

    [wind, direc, t, pr, tem, sol, the, qr, pre] = get_model_winds(
        lon, lat, t_orig, t_final, weather_path)

    ## TODO: Fix this. It produces a warning exception:
    ## FutureWarning: elementwise comparison failed; returning scalar instead,
    ## but in the future will perform elementwise comparison
    if inds == 'all':
        inds = np.array([0, np.shape(wind)[0] - 1])
    # Calculate U and V
    uwind = np.mean(
        wind[inds[0]:inds[-1] + 1]
        * np.cos(np.radians(direc[inds[0]:inds[-1] + 1])))
    uwind = np.array([uwind])
    vwind = np.mean(
        wind[inds[0]:inds[-1] + 1]
        * np.sin(np.radians(direc[inds[0]:inds[-1] + 1])))
    vwind = np.array([vwind])

    # Arrows
    ax.arrow(
        lon, lat, scale * uwind[0], scale * vwind[0],
        head_width=0.05, head_length=0.1, width=0.02,
        color='white', fc='DarkMagenta', ec='black')
    tplot = t[inds[0]:inds[-1] + 1]

    return tplot


def isolate_wind_timing(
        name, grid_T, grid_B, weather_path, t, hour=4, average=True):
    """Isolates indices timing of wind vectors. The timing is based on x number
    of hours before the max water level at a station.

    :arg str name: The name of the station, Point Atkinson, Victora,
                   Campbell River are good choices.

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg str weather_path: Path to the weather forcing files.

    :arg t: An array of outut times from the NEMO model.
    :type t: numpy array consisting of datetime objects

    :arg int hour: The number of hours before max ssh to plt.

    :arg average: Flag to determine if plotting should be averaged over
                  x hours before ssh or just a single time.
    :type average: boolean
                   (True=average over times,
                   False = only a single time_counter)

    :returns: inds, an array with the start and end index for plotting winds.
    """

    lat = SITES[name]['lat']
    lon = SITES[name]['lon']

    # Bathymetry
    bathy, X, Y = tidetools.get_bathy_data(grid_B)

    # Get sea surface height
    j, i = tidetools.find_closest_model_point(
        lon, lat, X, Y, bathy, allow_land=False)
    ssh = grid_T.variables['sossheig'][:, j, i]

    # "Place holder" residual so function can be used
    placeholder_res = np.zeros_like(ssh)

    # Index at which sea surface height is at its maximum at Point Atkinson
    max_ssh, index_ssh, tmax, max_res, max_wind, ind_w = get_maxes(
        ssh, t, placeholder_res, lon, lat, weather_path)

    # Build indices based on x hours before max ssh if possible. If not, start
    # at beginning of file.
    if ind_w > hour:
        inds = np.array([ind_w[0] - hour, ind_w])
    else:
        inds = np.array([0, ind_w])
    if not(average):
        inds = np.array([inds[0]])

    return inds


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


def plot_wind_arrow(
    ax, lon, lat, u_wind, v_wind,
    colours=COLOURS,
    wind_arrow_scale_factor=0.1,
):
    """Draw a wind arrow on an plot axes.

    The axes is assumed to be using lon/lat scales.

    This just a wrapper that applies particular formatting to the
    :py:meth:`matplotlib.axes.arrow` method.

    :arg ax: Plot axes to draw the arrow on.
    :type ax: :py:class:`matplotlib.axes.Axes`

    :arg float lon: Longitude of the arrow starting point.

    :arg float lat: Latitude of the arrow starting point.

    :arg float u_wind: Zonal (u) direction component of wind speed;
                       value will be scaled to give longitude direction
                       length of arrow.

    :arg float v_wind: Meridional (v) direction component of wind speed;
                       value will be scaled to give latitude direction
                       length of arrow.

    :arg dict colours: Colours to use for the arrow face and edge colours.
                       Defaults to :py:data:`figures.COLOURS`.

    :arg float wind_arrow_scale_factor: Scale factor applied to wind
                                        speed components to convert them
                                        to lon/lat scale of plot;
                                        defaults to 0.1.
    """
    ax.arrow(
        lon, lat,
        wind_arrow_scale_factor * u_wind,
        wind_arrow_scale_factor * v_wind,
        head_width=0.05, head_length=0.1, width=0.02,
        facecolor=colours['wind arrow']['facecolor'],
        edgecolor=colours['wind arrow']['edgecolor'])


## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as storm_surge_alerts_thumbnail module
def website_thumbnail(
    grid_B, grid_T, grids, weather_path, coastline, tidal_predictions,
    colours=COLOURS,
    fonts=FONTS,
    figsize=(18, 20),
):
    """Thumbnail for the UBC Storm Surge website includes the thresholds
    indicating the risk of flooding in three stations and the wind speeds and
    directions. It also includes a brief description of threshold colours.

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.  ***NOT
    USED***
    :type grid_B: :class:`netCDF4.Dataset`

    :arg grid_T: Hourly tracer results dataset from NEMO.           ***NOT
    USED***
    :type grid_T: :class:`netCDF4.Dataset`

    :arg dict grids: high frequency model results

    :arg str weather_path: The directory where weather forcing wind files
                           are stored.

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    :arg str tidal_predictions: Path to directory of tidal prediction
                                 file.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :returns: matplotlib figure object instance (fig).
    """
    fig = plt.figure(figsize=figsize, facecolor=colours['figure']['facecolor'])
    gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 1], height_ratios=[6, 1])
    gs.update(hspace=0.15, wspace=0.05)
    ax = fig.add_subplot(gs[0, :])
    shared.plot_map(ax, coastline)
    ax.set_xlabel('Longitude', **axis_font)
    ax.set_ylabel('Latitude', **axis_font)
    ax.grid()
    viz_tools.set_aspect(ax)
    for name in TIDAL_SITES:
        ssh_ts = nc_tools.ssh_timeseries_at_point(
            grids[name], 0, 0, datetimes=True)
        ttide = shared.get_tides(name, tidal_predictions)
        max_ssh, max_ssh_time = shared.find_ssh_max(name, ssh_ts, ttide)
        risk_level = stormtools.storm_surge_risk_level(name, max_ssh, ttide)
        plot_risk_level_marker(ax, name, risk_level, colours, 'o', 70, 0.3)
        lon, lat = PLACES[name]['lon lat']
        u_wind_4h_avg, v_wind_4h_avg = wind_tools.calc_wind_avg_at_point(
            arrow.get(max_ssh_time), weather_path,
            PLACES[name]['wind grid ji'], avg_hrs=-4)
        plot_wind_arrow(ax, lon, lat, u_wind_4h_avg, v_wind_4h_avg, colours)
    # Wind speed legend
    legend_wind_speed = 5  # m/s or knots
    plot_wind_arrow(ax, -122.2, 50.6, 0, -legend_wind_speed, colours)
    ax.text(-122.28, 50.55, "Reference: 5 m/s", rotation=90, fontsize=20)
    plot_wind_arrow(
        ax, -122.45, 50.6, 0, -unit_conversions.knots_mps(legend_wind_speed),
        colours)
    ax.text(-122.53, 50.55, "Reference: 5 knots", rotation=90, fontsize=20)
    # Title and axis spines, ticks & labels colours
    ax.set_title(
        'Marine and Atmospheric Conditions\n {:%A, %B %d, %Y}'
        .format(ssh_ts.time[0]),
        **fonts['website_thumbnail_title'])
    website_theme.set_axis_colors(ax)
    # Location labels
    ax.text(
        -125.7, 47.7,
        'Pacific\nOcean',
        fontsize=30, color=colours['figure']['location label'])
    ax.text(
        -123.2, 50.1,
        '  British\nColumbia',
        fontsize=30, color=colours['figure']['location label'])
    ax.text(
        -124.2, 47.8, 'Washington\n      State',
        fontsize=30, color=colours['figure']['location label'])
    ax.text(
        -122.3, 47.65, ' Puget\nSound',
        fontsize=20, color=colours['figure']['location label'])
    ax.text(
        -124.35, 48.325,
        '    Strait of\nJuan de Fuca',
        fontsize=20, color=colours['figure']['location label'], rotation=-18)
    ax.text(
        -124, 49.3,
        'Strait of\nGeorgia',
        fontsize=20, color=colours['figure']['location label'], rotation=-12)
    # Risk level legend
    axes = [fig.add_subplot(gs[1, i]) for i in range(3)]
    risk_level_colours = (
        colours['risk level colours'][None],
        colours['risk level colours']['moderate risk'],
        colours['risk level colours']['extreme risk'],
    )
    for ax, risk_level_colour in zip(axes, risk_level_colours):
        plt.setp(list(ax.spines.values()), visible=False)
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.set_axis_bgcolor(colours['figure']['facecolor'])
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.plot(
            0.2, 0.5,
            marker='o', markersize=70, markeredgewidth=2,
            color=risk_level_colour, alpha=0.6)
    axes[0].text(
        0.4, 0.2, 'Green:\nNo flooding\nrisk', fontsize=25, color='w')
    axes[1].text(
        0.4, 0.2, 'Yellow:\nRisk of\nhigh water', fontsize=25, color='w')
    axes[2].text(
        0.4, 0.2, 'Red:\nExtreme risk\nof flooding', fontsize=25, color='w')
    return fig


## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as pt_atkinson_tide module
def PA_tidal_predictions(
    grid_T, tidal_predications, PST=1, MSL=0, figsize=(20, 5),
):
    """Plots the tidal cycle at Point Atkinson during a 4 week period centred
    around the simulation start date.

    This function assumes that a tidal prediction file exists in a
    specific directory.
    Tidal predictions were calculated with ttide based on a time series
    from 2013.
    Plots are of predictions caluclated with all consituents.

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg str tidal_predications: Path to directory of tidal prediction
                                 file.

    :arg int PST: Specifies if plot should be presented in PST.
                  1 = plot in PST, 0 = plot in UTC.

    :arg int MSL: Specifies if the plot should be centred about mean sea level.
                  1=centre about MSL, 0=centre about 0.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :returns: matplotlib figure object instance (fig).
    """

    # Time range
    t_orig, t_end, t_nemo = get_model_time_variables(grid_T)
    timezone = PST * '[PST]' + abs((PST - 1)) * '[UTC]'

    # Axis limits are set as 2 weeks before and after start date.
    ax_start = t_orig - datetime.timedelta(weeks=2)
    ax_end = t_orig + datetime.timedelta(weeks=2)
    ylims = [-3, 3]

    # Figure
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1, 1, 1)
    fig.patch.set_facecolor('#2B3E50')
    fig.autofmt_xdate()
    plot_tides(ax, 'Point Atkinson', PST, MSL, tidal_predications, 'black')

    # Line indicating current date
    ax.plot([t_orig + time_shift * PST, t_orig + time_shift * PST],
            ylims, '-r', lw=2)
    ax.plot([t_end + time_shift * PST, t_end + time_shift * PST],
            ylims, '-r', lw=2)

    # Axis
    ax.set_xlim([ax_start + time_shift * PST, ax_end + time_shift * PST])
    ax.set_ylim(ylims)
    ax.set_title(
        'Tidal Predictions at Point Atkinson: ' + t_orig.strftime('%d-%b-%Y'),
        **title_font)
    ax.set_ylabel('Sea Surface Height [m]', **axis_font)
    ax.set_xlabel('Time {}'.format(timezone), **axis_font)
    ax.grid()
    axis_colors(ax, 'gray')
    ax.text(
        1., -0.2,
        'Tidal predictions calculated with t_tide: '
        'http://www.eos.ubc.ca/~rich/#T_Tide\n'
        'using CHS tidal constituents',
        horizontalalignment='right',
        verticalalignment='top',
        transform=ax.transAxes, color='white')

    return fig

## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as compare_water_levels module
def compare_water_levels(
        grid_T, grid_B, grids, coastline, PST=1, figsize=(20, 15)):
    """Compares modelled water levels to observed water levels and tides at a
    NOAA station over one day.

    See: http://tidesandcurrents.noaa.gov/stations.html?type=Water+Levels

    This function applies to stations at Cherry Point, Neah Bay,
    and Friday Harbor.

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg grids: high frequency model results
    :type grids: dictionary

    :arg PST: Specifies if plot should be presented in PST.
              1 = plot in PST, 0 = plot in UTC.
    :type PST: 0 or 1

    :arg figsize:  Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    # Bathymetry
    bathy, X, Y = tidetools.get_bathy_data(grid_B)

    # Time range
    t_orig, t_final, t = get_model_time_variables(grid_T)
    start_date = t_orig.strftime('%d-%b-%Y')
    end_date = t_final.strftime('%d-%b-%Y')
    timezone = PST * '[PST]' + abs((PST - 1)) * '[UTC]'

    # Figure
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor('#2B3E50')
    gs = gridspec.GridSpec(3, 2, width_ratios=[1.5, 1])
    gs.update(wspace=0.17, hspace=0.2)

    # Map
    ax0 = fig.add_subplot(gs[:, 1])
    _plot_stations_map(ax0, coastline, title='Station Locations')

    # Citation
    ax0.text(
        0.03, -0.45,
        'Observed water levels and tidal predictions from NOAA:\n'
        'http://tidesandcurrents.noaa.gov/stations.html?type=Water+Levels',
        horizontalalignment='left',
        verticalalignment='top',
        transform=ax0.transAxes, color='white')

    m = np.arange(3)
    names = ['Neah Bay', 'Friday Harbor', 'Cherry Point']

    for name, M in zip(names, m):
        lat = SITES[name]['lat']
        lon = SITES[name]['lon']
        # Map
        ax0.plot(lon, lat, marker='D', color='DarkMagenta',
                 markersize=10, markeredgewidth=2)
        bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.8)
        ax0.annotate(name, (lon - 0.05, lat - 0.15), fontsize=15,
                     color='black', bbox=bbox_args)

        # NOAA
        obs = get_NOAA_wlevels(SITES[name]['stn_no'], start_date, end_date)
        tides = get_NOAA_tides(SITES[name]['stn_no'], start_date, end_date)

        # Get sea surface height
        ssh, t = load_model_ssh(grids[name])

        # Sea surface height plots
        ax = fig.add_subplot(gs[M, 0])
        ax.plot(
            t[:] + time_shift * PST, ssh,
            c=model_c, linewidth=2, label='Model')
        ax.plot(
            obs.time[:] + time_shift * PST, obs.wlev, c=observations_c,
            linewidth=2, label='Observed water levels')
        ax.plot(
            tides.time + time_shift * PST, tides.pred, c=predictions_c,
            linewidth=2, label='Tidal predictions')

        # Axis
        ax.set_xlim(t_orig + time_shift * PST, t_final + time_shift * PST)
        ax.set_ylim([-3, 3])
        ax.set_title(
            'Hourly Sea Surface Height at {name}: {t_orig:%d-%b-%Y}'
            .format(name=name, t_orig=t_orig),
            **title_font)
        ax.set_ylabel('Water Levels wrt MSL (m)', **axis_font)
        ax.set_xlabel('Time {}'.format(timezone), **axis_font)
        ax.grid()
        axis_colors(ax, 'gray')
        ax.xaxis.set_major_formatter(hfmt)
        fig.autofmt_xdate()
        if M == 0:
            legend = ax.legend(
                bbox_to_anchor=(1.285, 1), loc=2, borderaxespad=0.,
                prop={'size': 15}, title=r'Legend')
            legend.get_title().set_fontsize('20')

    return fig

## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as compare_tide_prediction_max_ssh module
def compare_tidalpredictions_maxSSH(
    grid_T, grid_B, grids, weather_path, tidal_predications,
    PST=1, MSL=0, name='Point Atkinson', figsize=(20, 12),
):
    """Plots a map for sea surface height when it was at its maximum at Point
    Atkinson and compares modelled water levels to tidal predications over one
    day.

    It is assummed that the tidal predictions were calculated ahead of
    time and stored in a very specific location.
    The tidal predictions were calculated with all constituents using
    ttide based on a time series from 2013.
    The corrected model takes into account errors resulting in using
    only 8 constituents.
    The residual is calculated as corrected model - tides
    (with all constituents).

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg dict grids: high frequency model results

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg str tidal_predications: Path to directory of tidal prediction
                                 file.

    :arg int PST: Specifies if plot should be presented in PST.
                  1 = plot in PST, 0 = plot in UTC.

    :arg int MSL: Specifies if the plot should be centred about mean sea level.
                  1=centre about MSL, 0=centre about 0.

    :arg str name: Name of station.

    :arg 2-tuple figsize:  Figure size (width, height) in inches.

    :returns: matplotlib figure object instance (fig).
    """

    # Stations information
    lat = SITES[name]['lat']
    lon = SITES[name]['lon']

    # Time range
    t_orig, t_final, thourly = get_model_time_variables(grid_T)
    tzone = PST * '[PST]' + abs((PST - 1)) * '[UTC]'

    # Bathymetry
    bathy, X, Y = tidetools.get_bathy_data(grid_B)

    # Get sea surface height
    ssh_loc, t = load_model_ssh(grids[name])
    # full field
    ssh = grid_T.variables['sossheig'][:]

    # Figure
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor('#2B3E50')
    gs = gridspec.GridSpec(3, 2, width_ratios=[2, 1])
    gs.update(wspace=0.13, hspace=0.2)
    ax0 = fig.add_subplot(gs[0, 0])  # information box
    axis_colors(ax0, 'blue')
    plt.setp(
        list(ax0.spines.values()),
        visible=False)  # hide axes for information box
    ax0.xaxis.set_visible(False)
    ax0.yaxis.set_visible(False)
    ax1 = fig.add_subplot(gs[1, 0])  # sea surface height
    ax2 = fig.add_subplot(gs[:, 1])  # map
    ax3 = fig.add_subplot(gs[2, 0])  # residual

    # Sea surface height plot
    ttide = plot_tides(ax1, name, PST, MSL, tidal_predications)
    ssh_corr = plot_corrected_model(
        ax1, t, ssh_loc, ttide, PST, MSL, SITES[name]['msl'])
    ax1.plot(
        t + PST * time_shift, ssh_loc,
        '--', c=model_c, linewidth=1, label='Model')

    # Compute residual
    res = compute_residual(ssh_corr, t, ttide)

    # Find maximim sea surface height and timing
    max_ssh, index, tmax, max_res, max_wind, ind_w = get_maxes(
        ssh_corr, t, res, lon, lat, weather_path)
    ax0.text(0.05, 0.9, name, fontsize=20,
             horizontalalignment='left',
             verticalalignment='top', color='white')
    ax0.text(0.05, 0.75,
             'Max SSH: {:.2f} metres above mean sea level'.format(max_ssh),
             fontsize=15, horizontalalignment='left',
             verticalalignment='top', color='white')
    ax0.text(
        0.05, 0.6,
        'Time of max: {time} {timezone}'
        .format(
            time=(tmax + PST * time_shift).strftime('%Y-%m-%d %H:%M'),
            timezone=PST * '[PST]' + abs((PST - 1)) * '[UTC]'),
        fontsize=15, horizontalalignment='left',
        verticalalignment='top', color='white')
    ax0.text(0.05, 0.45,
             'Residual: {:.2f} metres'.format(max_res),
             fontsize=15, horizontalalignment='left',
             verticalalignment='top', color='white')
    ax0.text(0.05, 0.3,
             'Wind speed: {:.1f} m/s'.format(float(max_wind)),
             fontsize=15, horizontalalignment='left',
             verticalalignment='top', color='white')

    # Mark point for maximum ssh
    ax1.plot(tmax + PST * time_shift, max_ssh, color='white', marker='o',
             markersize=10, markeredgewidth=3, label='Maximum SSH')

    # Axis for sea surface height plot
    ax1.set_xlim(t_orig + PST * time_shift, t_final + PST * time_shift)
    ax1.set_ylim([-3, 3])
    ax1.set_title(
        'Hourly Sea Surface Height at {name}: {t_orig:%d-%b-%Y}'
        .format(name=name, t_orig=t_orig),
        **title_font)
    ax1.set_xlabel('Time {}'.format(tzone), **axis_font)
    ax1.set_ylabel('Water Levels wrt MSL (m)', **axis_font)
    ax1.grid()
    ax1.legend(loc=0, numpoints=1)
    axis_colors(ax1, 'gray')
    ax1.xaxis.set_major_formatter(hfmt)

    # Plot Residual
    ax3.plot(t + PST * time_shift, res, '-k', linewidth=2, label='Residual')

    # Axis for residual plot
    ax3.set_xlim(t_orig + PST * time_shift, t_final + PST * time_shift)
    ax3.set_ylim([-1, 1])
    ax3.set_xlabel('Time {}'.format(tzone), **axis_font)
    ax3.set_ylabel('Residual (m)', **axis_font)
    ax3.set_yticks(np.arange(-1.0, 1.25, 0.25))
    ax3.grid()
    ax3.legend(loc=0, numpoints=1)
    axis_colors(ax3, 'gray')
    ax3.xaxis.set_major_formatter(hfmt)
    fig.autofmt_xdate()

    # Map of sea surface height
    cs = [-1, -0.5, 0.5, 1, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.4, 2.6]
    [j, i] = tidetools.find_closest_model_point(lon, lat, X, Y, bathy)
    hourly_maxssh = np.argmax(ssh[:, j, i])

    ssh_max_field = np.ma.masked_values(ssh[hourly_maxssh], 0)
    mesh = ax2.contourf(
        ssh_max_field, cs,
        cmap='nipy_spectral', extend='both', alpha=0.6)
    ax2.contour(ssh_max_field, cs, colors='k', linestyles='--')

    cbar = fig.colorbar(mesh, ax=ax2)
    cbar.set_ticks(cs)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    cbar.set_label('[m]', color='white')
    # Time for map
    tmap = thourly[hourly_maxssh]

    ax2.set_title(
        'Sea Surface Height: {:%d-%b-%Y, %H:%M}'
        .format(tmap + PST * time_shift),
        **title_font)
    ax2.set_xlabel('X Index', **axis_font)
    ax2.set_ylabel('Y Index', **axis_font)
    ax2.grid()

    axis_colors(ax2, 'white')
    viz_tools.plot_coastline(ax2, grid_B)
    viz_tools.plot_land_mask(ax2, grid_B, color='burlywood')
    ax2.plot(i, j,
             marker='o', markersize=10, markeredgewidth=3,
             color='white')

    return fig

## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as water_level_thresholds module
def plot_thresholds_all(
    grid_T, grid_B, grids, weather_path, coastline, tidal_predications,
    PST=1, MSL=1, figsize=(20, 25),
):
    """Plots sea surface height over one day with respect to warning
    thresholds.

    This function applies only to Point Atkinson, Campbell River, and Victoria.
    8/25/15: added Nanaimo and Cherry Point
    There are three different warning thresholds.
    The locations of stations are colored depending on the threshold in
    which they fall: green, yellow, red.

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    :arg str tidal_predications: Path to directory of tidal prediction
                                 file.

    :arg int PST: Specifies if plot should be presented in PST.
                  1 = plot in PST, 0 = plot in UTC.

    :arg int MSL: Specifies if the plot should be centred about mean sea level.
                  1=centre about MSL, 0=centre about 0.

    :arg 2-tuple figsize:  Figure size (width, height) in inches.

    :returns: matplotlib figure object instance (fig).
    """

    # Figure set up
    fig = plt.figure(figsize=figsize, facecolor='#2B3E50')
    gs = gridspec.GridSpec(5, 2, width_ratios=[1.5, 1])
    gs.update(wspace=0.13, hspace=0.2)
    bbox_args = dict(boxstyle='square', facecolor='white', alpha=0.8)

    # Map of region
    ax0 = fig.add_subplot(gs[:, 1])
    _plot_stations_map(
        ax0, coastline, title='Degree of Flood Risk',
        xlim=(-125.4, -122.2), ylim=(48, 50.3))

    # Bathymetry and model time
    bathy, X, Y = tidetools.get_bathy_data(grid_B)
    t_orig, t_final, t = get_model_time_variables(grid_T)
    tzone = '[PST]' if PST else '[UTC]'
    t_shift = time_shift if PST else 0

    for M, name in enumerate(TIDAL_SITES):
        # Get sea surface height
        ssh_loc, t = load_model_ssh(grids[name])
        msl = SITES[name]['msl']

        # Plot tides, corrected model and original model
        ax = fig.add_subplot(gs[M, 0])
        if name == 'Point Atkinson':
            plot_PA_observations(ax, PST)
        ttide = plot_tides(ax, name, PST, MSL, tidal_predications)
        ssh_corr = plot_corrected_model(ax, t, ssh_loc, ttide, PST, MSL, msl)
        ax.plot(
            t + t_shift, ssh_loc + msl*MSL, '--',
            c=model_c, lw=1, label='Model')

        # Define and plot thresholds on map and in sea surface height plots
        thresholds = plot_threshold_map(
            ax0, ttide, ssh_corr, 'D', 10, 1.0, name)
        ax0.annotate(
            name, (SITES[name]['lon'], SITES[name]['lat']),
            fontsize=15, color='black', bbox=bbox_args,
            textcoords='offset points', xytext=(15, 0.8))
        colors = ['Gold', 'Red', 'DarkRed']
        labels = ['Maximum tides', 'Extreme water', 'Historical maximum']
        for wlev, color, label in zip(thresholds, colors, labels):
            ax.axhline(y=wlev, color=color, lw=2, ls='solid', label=label)

        # Legend
        if M == 0:
            legend = ax.legend(
                bbox_to_anchor=(1.285, 1), loc=2, borderaxespad=0.,
                prop={'size': 15}, title=r'Legend')
            legend.get_title().set_fontsize('20')

        # Axis formatting
        ax.set_xlim(t_orig + t_shift, t_final + t_shift)
        ax.set_ylim([-1, 6])
        ax.set_title(
            'Hourly Sea Surface Height at {name}: {t_orig:%d-%b-%Y}'
            .format(name=name, t_orig=t_orig),
            **title_font)
        ax.set_xlabel('Time {}'.format(tzone), **axis_font)
        ax.set_ylabel('Water Level above Chart Datum (m)', **axis_font)
        ax.grid()
        axis_colors(ax, 'gray')
        ax.xaxis.set_major_formatter(hfmt)

    # Citation
    ax0.text(0.03, -0.45,
             'Tidal predictions calculated with t_tide: '
             'http://www.eos.ubc.ca/~rich/#T_Tide \n'
             'using CHS tidal constituents \n'
             'Observed water levels from Fisheries and Oceans, Canada \n'
             'via Scott Tinis at stormsurgebc.ca',
             horizontalalignment='left',
             verticalalignment='top',
             transform=ax0.transAxes, color='white')
    fig.autofmt_xdate()

    return fig

## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as sandheads_winds
def Sandheads_winds(
        grid_T, grid_B, weather_path, coastline, PST=1, figsize=(20, 12)):
    """Plots the observed and modelled winds at Sandheads during the
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
    ax1.set_title('Winds at Sandheads:  ' + start, **title_font)
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
    ax2.set_ylabel('Wind Direction \n (degress CCW of East)', **axis_font)
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
        'Sandheads', (lon - 0.05, lat - 0.15),
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

## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as wind_vectors_at_stations module
## TODO: Refactor to separate averaged and wind at time functionality
## TODO: Maybe refactor to accept a list of stations instead of one or 'all'
def winds_average_max(
        grid_T, grid_B, weather_path, coastline, station, wind_type,
        figsize=(20, 15)):
    """Plots wind vectors at several stations over domain. Wind vectors can be
    averaged over the entire simulation or plotted at 4 hours before max ssh
    at Point Atkinson

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg station: Name of one station or 'all' for all stations.
    :type station: string

    :arg wind_type: specifies average winds or max winds
    :type wind_type: string, 'average' or 'max'

    :arg figsize:  Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    # Map
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1, 1, 1)
    fig.patch.set_facecolor('#2B3E50')
    shared.plot_map(ax, coastline)
    ax.set_xlabel('Longitude', **axis_font)
    ax.set_ylabel('Latitude', **axis_font)
    ax.grid()
    viz_tools.set_aspect(ax)
    scale = 0.1
    # Reference for m/s
    ax.arrow(-122.5, 50.65, 0. * scale, -5. * scale,
             head_width=0.05, head_length=0.1, width=0.02,
             color='white', fc='DarkMagenta', ec='black')
    ax.text(-122.58, 50.5, "Reference: 5 m/s", rotation=90, fontsize=14)
    # Reference for knots
    ax.arrow(-122.75, 50.65, 0. * scale * k2ms, -5. * scale * k2ms,
             head_width=0.05, head_length=0.1, width=0.02,
             color='white', fc='DarkMagenta', ec='black')
    ax.text(-122.83, 50.5, "Reference: 5 knots", rotation=90, fontsize=14)

    # Stations
    if station == 'all':
        names = WIND_SITES
        colors = stations_c
    else:
        names = [station]
        colors = ['DarkMagenta']

    # Indices
    t_orig, t_final, t = get_model_time_variables(grid_T)
    if wind_type == 'max':
        inds = isolate_wind_timing(
            'Point Atkinson', grid_T, grid_B, weather_path, t, 4,
            average=False)
    elif wind_type == 'average':
        inds = 'all'

    # Plot
    for name, station_c in zip(names, colors):
        lat = SITES[name]['lat']
        lon = SITES[name]['lon']
        plot_time = plot_wind_vector(
            ax, name, t_orig, t_final, weather_path, inds, scale)
        ax.plot(
            lon, lat,
            marker='D', markersize=14, markeredgewidth=2,
            color=station_c, label=name)

    # Figure format
    t1 = (plot_time[0] + time_shift).strftime('%d-%b-%Y %H:%M')
    t2 = (plot_time[-1] + time_shift).strftime('%d-%b-%Y %H:%M')
    legend = ax.legend(
        numpoints=1, bbox_to_anchor=(0.9, 1.05), loc=2, borderaxespad=0.,
        prop={'size': 15}, title=r'Stations')
    legend.get_title().set_fontsize('20')
    if wind_type == 'max':
        ax.set_title('Modelled winds at \n {time} [PST]'
                     .format(time=t1),
                     **title_font)
    elif wind_type == 'average':
        ax.set_title('Modelled winds averaged over \n {t1} [PST] to {t2} [PST]'
                     .format(t1=t1, t2=t2),
                     **title_font)
    axis_colors(ax, 'gray')

    # Citation
    ax.text(0.6, -0.07,
            'Modelled winds are from the High Resolution Deterministic '
            'Prediction System\n'
            'of Environment Canada: '
            'https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html',
            horizontalalignment='left',
            verticalalignment='top',
            transform=ax.transAxes, color='white')

    return fig


def add_bathy_patch(distance, grid_B, lines,  ax, color='burlywood',
                    zmin=-450):
    """Add a polygon shaped as the land in the thalweg section

    :arg distance: distance along thalwrg in km
    :type distance: 2D numpy array

    :arg grid_B: bathymetry file
    :type grid_B: netCDF handle

    :arg lines: indices for the thalweg
    :type lines: 2D numpy array

    :arg ax: axis to plot in
    :type ax: axis handle

    :arg color: color of bathymetry patch
    :type color: string

    :arg zmin: minimum depth for plot in meters (use negative convention)
    :type zmin: float
    """
    # Look up bottom bathymetry along thalweg
    depth = grid_B.variables['Bathymetry'][:]
    thalweg_bottom = -depth[lines[:, 0], lines[:, 1]]
    # Construct bathy polygon
    poly = np.zeros((thalweg_bottom.shape[0]+2, 2))
    poly[0, 0] = 0
    poly[0, 1] = zmin
    poly[1:-1, 0] = distance[0, :]
    poly[1:-1, 1] = thalweg_bottom
    poly[-1, 0] = distance[0, -1]
    poly[-1, 1] = zmin
    # Add polygon patch to plot
    ax.add_patch(patches.Polygon(poly, facecolor=color,
                                 edgecolor=color))

## Called by make_plots (research)

## TODO: Move/rename to figures.research as thalweg_salinity module
def thalweg_salinity(
    grid_T_d, mesh_mask, grid_B,
    thalweg_pts_file='/data/nsoontie/MEOPAR/tools/bathymetry/thalweg_working.txt',
    salinity_levels=[
        26, 27, 28, 29, 30, 30.2, 30.4, 30.6, 30.8, 31, 32, 33, 34],
    cmap='hsv',
    colours=COLOURS,
    figsize=(20, 8),
):
    """Plot the daily average salinity field along the thalweg with
    coloured contours.

    :arg str thalweg_pts_file: Path and file name to read the array of
                               thalweg grid point from.

    :arg grid_T_d: Daily tracer results dataset from NEMO.
    :type grid_T_d: :py:class:`netCDF4.Dataset`

    :arg list salinity_levels: Salinity values for contour levels shading.

    :arg mesh_mask: NEMO mesh_mask file.
    :type mesh_mask: :class:`netCDF4.Dataset`

    :arg grid_B: Model bathymetry file.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg cmap: Colour map to use for the contour shading.
    :type cmap: str or :py:class:`matplotlib.colors.Colormap`

    :arg dict colours: Colours to use for various elements of the figure.
                       Defaults to :py:data:`figures.colours`.

    :arg 2-tuple figsize:  Figure size (width, height) in inches.

    :returns: :py:class:`matplotlib.Figure.figure`
    """

    # Look up depth of tcells and thalweg points.
    dep_d = mesh_mask.variables['gdept'][0, :, :, :]
    thalweg_pts = np.loadtxt(thalweg_pts_file, delimiter=' ', dtype=int)

    # Tracer data
    salinity = grid_T_d.variables['vosaline'][:]
    lons = grid_T_d.variables['nav_lon'][:]
    lats = grid_T_d.variables['nav_lat'][:]

    # Actual bathy
    depth_bathy = grid_B.variables['Bathymetry'][:]
    depth_bathy = depth_bathy[thalweg_pts[:, 0], thalweg_pts[:, 1]]

    # Salinity along thalweg
    salinity = salinity[0, :, thalweg_pts[:, 0], thalweg_pts[:, 1]]
    salinity = fill_in_bathy(salinity, mesh_mask, thalweg_pts)
    salinity = np.ma.masked_values(salinity, 0)
    dep_d = -dep_d[:, thalweg_pts[:, 0], thalweg_pts[:, 1]]
    # Calculate distance along thalweg and expand into same shape as depth
    distance = thalweg_distance(lons[thalweg_pts[:, 0], thalweg_pts[:, 1]],
                                lats[thalweg_pts[:, 0], thalweg_pts[:, 1]])
    distance = np.expand_dims(distance, 0)
    distance = distance + np.zeros(dep_d.shape)
    # Figure
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.set_facecolor(colours['figure']['facecolor'])
    mesh = ax.contourf(distance, dep_d, salinity.T, salinity_levels,
                       cmap=cmap, extend='both')
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_ticks(salinity_levels)
    cbar.set_label(
        'Practical Salinity [psu]',
        color=colours['cbar']['label'], **axis_font)
    cbar.ax.axes.tick_params(labelcolor=colours['cbar']['tick labels'])

    timestamp = nc_tools.timestamp(grid_T_d, 0)
    ax.set_title(
        'Salinity field along thalweg: ' +
        timestamp.format('DD-MMM-YYYY'),
        **title_font)
    ax.set_ylabel('Depth [m]', **axis_font)
    ax.set_xlabel('Distance along Thalweg (km)', **axis_font)
    axis_colors(ax, 'white')
    # Add the bathymetry patch
    add_bathy_patch(distance, grid_B, thalweg_pts, ax)

    return fig


def thalweg_distance(lons, lats):
    """Calculate cumulative distance between points in lons, lats

    :arg lons: longitude points
    :type lons: numpy array

    :arg lats: latitude points
    :type lats: numpy array

    :returns: dist, a numpy array with distance along track
    """
    dist = [0]
    for i in np.arange(1, lons.shape[0]):
        newdist = dist[i-1] + tidetools.haversine(lons[i], lats[i],
                                                  lons[i-1], lats[i-1])
        dist.append(newdist)
    dist = np.array(dist)
    return dist


def fill_in_bathy(variable, mesh_mask, lines):
    """For each horizontal point in variable, fill in first vertically masked
    point with the value just above.
    Use mbathy in mesh_mask file to determine level of vertical masking

    :arg variable: the variable to be filled
    :type variable: 2D numpy array

    :arg mesh_mask: NEMO mesh_mask file
    :type mesh_mask: netCDF handle

    :arg lines: indices for the thalweg
    :type lines: 2D numpy array

    :returns: newvar, the filled numpy array
    """
    mbathy = mesh_mask.variables['mbathy'][0, :, :]
    newvar = np.copy(variable)

    mbathy = mbathy[lines[:, 0], lines[:, 1]]
    for i, level in enumerate(mbathy):
        newvar[i, level] = variable[i, level-1]
    return newvar

## Called by make_plots (research)
## TODO: Move/rename to figures.research as thalweg_temperature module
def thalweg_temperature(
    grid_T_d, mesh_mask, grid_B,
    thalweg_pts_file='/data/nsoontie/MEOPAR/tools/bathymetry/thalweg_working.txt',
    figsize=(20, 8),
    cs = [6.9, 7, 7.5, 8, 8.5, 9, 9.8, 9.9, 10.3, 10.5, 11, 11.5, 12, 13, 14,
          15, 16, 17, 18, 19],
):
    """Plots the daily average temperature field along the thalweg.

    :arg grid_T_d: Daily tracer results dataset from NEMO.
    :type grid_T_d: :class:`netCDF4.Dataset`

    :arg mesh_mask: NEMO mesh_mask file.
    :type mesh_mask: :class:`netCDF4.Dataset`

    :arg grid_B: Model bathymetry file.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg figsize:  Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :arg cs: List of salinity contour levels for shading.
    :type cs: list

    :returns: matplotlib figure object instance (fig).
    """
    # Look up depth of tcells.
    dep_d = mesh_mask.variables['gdept'][0, :, :, :]

    # Tracer data
    temp_d = grid_T_d.variables['votemper'][:]
    lons = grid_T_d.variables['nav_lon'][:]
    lats = grid_T_d.variables['nav_lat'][:]

    # Call thalweg
    lines = np.loadtxt(thalweg_pts_file, delimiter=" ", unpack=False)
    lines = lines.astype(int)
    # Actual bathy
    depth_bathy = grid_B.variables['Bathymetry'][:]
    depth_bathy = depth_bathy[lines[:, 0], lines[:, 1]]

    # Temp along thalweg
    tempP = temp_d[0, :, lines[:, 0], lines[:, 1]]
    tempP = fill_in_bathy(tempP, mesh_mask, lines)
    tempP = np.ma.masked_values(tempP, 0)
    dep_d = -dep_d[:, lines[:, 0], lines[:, 1]]
    # Calculate distance along thalweg and expand into same shape as depth
    distance = thalweg_distance(lons[lines[:, 0], lines[:, 1]],
                                lats[lines[:, 0], lines[:, 1]])
    distance = np.expand_dims(distance, 0)
    distance = distance + np.zeros(dep_d.shape)
    # Figure
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.patch.set_facecolor('#2B3E50')
    mesh = ax.contourf(distance, dep_d, tempP.T, cs, cmap='jet', extend='both')
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_ticks(cs)
    cbar.set_label('Temperature [deg C]', color='white', **axis_font)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
    timestamp = nc_tools.timestamp(grid_T_d, 0)
    ax.set_title(
        'Temperature field along thalweg: ' +
        timestamp.format('DD-MMM-YYYY'),
        **title_font)
    ax.set_ylabel('Depth [m]', **axis_font)
    ax.set_xlabel('Distance along Thalweg [km]', **axis_font)
    axis_colors(ax, 'white')
    # Add the bathymetry patch
    add_bathy_patch(distance, grid_B, lines, ax)

    return fig

## Called by make_plots (research)
## TODO: Move/rename to figures.research as surface_daily_avg_s_t_currents module
def plot_surface(
    grid_T_d, grid_U_d, grid_V_d, grid_B,
    limits=[0, 398, 0, 898], figsize=(20, 12),
):
    """Plots the daily average surface salinity, temperature, and currents.

    :arg grid_T_d: Daily tracer results dataset from NEMO.
    :type grid_T_d: :class:`netCDF4.Dataset`

    :arg grid_U_d: Daily zonal velocity results dataset from NEMO.
    :type grid_U_d: :class:`netCDF4.Dataset`

    :arg grid_V_d: Daily meridional velocity results dataset from NEMO.
    :type grid_V_d: :class:`netCDF4.Dataset`

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg limits: Figure limits [xmin,xmax,ymin,ymax].
    :type limits: 2-tuple

    :arg figsize: Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    xmin = limits[0]
    xmax = limits[1]
    ymin = limits[2]
    ymax = limits[3]

    # Tracer data
    sal_d = grid_T_d.variables['vosaline']
    tem_d = grid_T_d.variables['votemper']

    # Bathymetry
    bathy, X, Y = tidetools.get_bathy_data(grid_B)

    # Preparing salinity and temperature
    t, z = 0, 0
    sal_d = np.ma.masked_values(sal_d[t, z], 0)
    tem_d = np.ma.masked_values(tem_d[t, z], 0)

    tracers = [sal_d, tem_d]
    titles = ['Average Salinity: ', 'Average Temperature: ']
    cmaps = ['spectral', 'jet']
    units = ['[PSU]', '[degC]']

    # Figure
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=figsize)
    fig.patch.set_facecolor('#2B3E50')

    axs = [ax1, ax2]
    plots = np.arange(1, 3, 1)

    for ax, tracer, title, cmap, unit, plot in zip(
            axs, tracers, titles, cmaps, units, plots):

        # Map
        cmap = plt.get_cmap(cmap)

        # Colormaps
        if plot == 1:   # salinity
            cs = np.arange(0, 33, 1)
            step = 4
        if plot == 2:   # temperature
            cs = np.arange(4, 21, 1)
            step = 2

        # Plot salinity and temperature
        mesh = ax.contourf(tracer, cs, cmap=cmap, vmin=cs[0], vmax=cs[-1],
                           extend='both')

        # Axis
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        cbar = fig.colorbar(mesh, ax=ax)
        timestamp = nc_tools.timestamp(grid_T_d, 0)
        ax.set_title(title + timestamp.format('DD-MMM-YYYY'), **title_font)
        ax.set_xlabel('X Index', **axis_font)
        ax.set_ylabel('Y Index', **axis_font)
        ax.grid()
        cbar.set_ticks(cs[::step])
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')
        cbar.set_label(unit, color='white', **axis_font)
        viz_tools.plot_coastline(ax, grid_B)
        axis_colors(ax, 'white')
        ax.set_axis_bgcolor('burlywood')

    # Preparing velocity
    ugrid = grid_U_d.variables['vozocrtx']
    vgrid = grid_V_d.variables['vomecrty']
    zlevels = grid_U_d.variables['depthu']
    t, zlevel = 0, 0

    y_slice = np.arange(0, ugrid.shape[2])
    x_slice = np.arange(0, ugrid.shape[3])

    arrow_step = 25
    y_slice_a = y_slice[::arrow_step]
    x_slice_a = x_slice[::arrow_step]

    ugrid_tzyx = np.ma.masked_values(ugrid[t, zlevel, y_slice_a, x_slice_a], 0)
    vgrid_tzyx = np.ma.masked_values(vgrid[t, zlevel, y_slice_a, x_slice_a], 0)

    u_tzyx, v_tzyx = viz_tools.unstagger(ugrid_tzyx, vgrid_tzyx)

    speeds = np.sqrt(np.square(u_tzyx) + np.square(v_tzyx))

    # Colormap
    cs = np.arange(0, .65, .05)

    # Plot velocity
    quiver = ax3.quiver(x_slice_a[1:], y_slice_a[1:], u_tzyx, v_tzyx, speeds,
                        pivot='mid', cmap='gnuplot_r', width=0.015)

    # Axis
    viz_tools.plot_land_mask(
        ax3,
        grid_B,
        xslice=x_slice,
        yslice=y_slice,
        color='burlywood')
    viz_tools.plot_coastline(ax3, grid_B)

    cbar = fig.colorbar(quiver, ax=ax3)
    cbar.set_ticks(cs)
    cbar.set_label('[m / s]', color='white', **axis_font)
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='w')

    ax3.set_xlim(x_slice[0], x_slice[-1])
    ax3.set_ylim(y_slice[0], y_slice[-1])
    plt.axis((xmin, xmax, ymin, ymax))
    ax3.grid()

    ax3.set_title(
        'Average Velocity Field: ' + timestamp.format('DD-MMM-YYYY')
        + u', depth\u2248{d:.2f} {z.units}'
        .format(d=zlevels[zlevel], z=zlevels), **title_font)
    ax3.set_xlabel('X Index', **axis_font)
    ax3.set_ylabel('Y Index', **axis_font)
    ax3.quiverkey(quiver, 355, 850, 1, '1 m/s', coordinates='data',
                  color='Indigo', labelcolor='black')
    axis_colors(ax3, 'white')

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


## Called by make_plots (publish)
## TODO: Move/rename to figures.publish as storm_surge_alerts
def plot_threshold_website(
    grid_B, grid_T, grids, weather_path, coastline, tidal_predictions,
    scale=0.1, PST=1, colours=COLOURS, fonts=FONTS, figsize=(18, 20),
):
    """Overview image for Salish Sea website.

    Plots a map of the Salish Sea with markers indicating extreme water
    at Point Atkinson, Victoria, Campbell River, Nanaimo and Cherry Point
    Also plots wind vectors averaged over 4 hours before the max ssh at
    each station.
    Includes text boxes with max water level and timing.

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg grid_T: Hourly tracer results dataset from NEMO.
    :type grid_T: :class:`netCDF4.Dataset`

    :arg dict grids: high frequency model results

    :arg str weather_path: The directory where the weather forcing files
                           are stored.

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    :arg str tidal_predictions: Path to directory of tidal prediction
                                 file.

    :arg float scale: scale factor or wind arrows

    :arg int PST: Specifies if plot should be presented in PST.
                  1 = plot in PST, 0 = plot in UTC.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :returns: matplotlib figure object instance (fig).
    """

    # Figure
    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 1], height_ratios=[6, 1])
    gs.update(hspace=0.1, wspace=0.05)
    ax = fig.add_subplot(gs[0, :])
    ax1 = fig.add_subplot(gs[1, 0])
    ax2 = fig.add_subplot(gs[1, 1])
    ax3 = fig.add_subplot(gs[1, 2])

    # Map
    shared.plot_map(ax, coastline)
    ax.set_xlabel('Longitude', **axis_font)
    ax.set_ylabel('Latitude', **axis_font)
    ax.grid()
    viz_tools.set_aspect(ax)

    max_ssh_time = {}
    max_ssh = {}
    max_windavg = {}
    for name in TIDAL_SITES:
        ssh_ts = nc_tools.ssh_timeseries_at_point(
            grids[name], 0, 0, datetimes=True)
        ttide = shared.get_tides(name, tidal_predictions)
        max_ssh[name], max_ssh_time[name] = shared.find_ssh_max(
            name, ssh_ts, ttide)
        risk_level = stormtools.storm_surge_risk_level(
                     name, max_ssh[name], ttide)
        plot_risk_level_marker(ax, name, risk_level, colours, 'o', 55, 0.3)
        lon, lat = PLACES[name]['lon lat']
        u_wind_4h_avg, v_wind_4h_avg = wind_tools.calc_wind_avg_at_point(
            arrow.get(max_ssh_time[name]), weather_path,
            PLACES[name]['wind grid ji'], avg_hrs=-4)
        plot_wind_arrow(ax, lon, lat, u_wind_4h_avg, v_wind_4h_avg, colours)
        max_windavg[name], _ = wind_tools.wind_speed_dir(
                               u_wind_4h_avg, v_wind_4h_avg)

    # Box for Winds
    textstr = "Winds are 4 hour\nAverage Before\nMaximum Sea Level"
    props = dict(facecolor='white')
    ax.text(0.8, 0.78, textstr, transform=ax.transAxes, fontsize=14,
            verticalalignment='top', bbox=props)
    # Legend SSH
    handles, labels = ax.get_legend_handles_labels()
    display = (0, 1, 2)
    green = plt.Line2D((0, 0), (0, 1),
                       color='green', marker='o', linestyle='', markersize=25,
                       alpha=0.5)
    yellow = plt.Line2D((0, 0), (0, 1),
                        color='Gold', marker='o', linestyle='', markersize=25,
                        alpha=0.5)
    red = plt.Line2D((0, 0), (0, 1),
                     color='red', marker='o', linestyle='', markersize=25,
                     alpha=0.5)
    legend = ax.legend([handle for j, handle in enumerate(handles)
                        if j in display] + [green, yellow, red],
                       [label for j, label in enumerate(labels)
                        if j in display] + ['No flooding\nrisk',
                                            'Risk of\nhigh water',
                                            'Extreme risk\nof flooding'],
                       numpoints=1, prop={'size': 15},
                       bbox_to_anchor=(0.9, 1.05), loc=2,
                       title=' Possible\nWarnings')
    legend.get_title().set_fontsize('20')

    # Reference arrow
    ax.arrow(-122.5, 50.65, 0. * scale, -5. * scale,
             head_width=0.05, head_length=0.1, width=0.02,
             color='white', fc='DarkMagenta', ec='black')
    ax.text(-122.58, 50.5, "Reference: 5 m/s", rotation=90, fontsize=14)

    # for knots
    ax.arrow(-122.75, 50.65, 0. * scale * k2ms, -5. * scale * k2ms,
             head_width=0.05, head_length=0.1, width=0.02,
             color='white', fc='DarkMagenta', ec='black')
    ax.text(-122.83, 50.5, "Reference: 5 knots", rotation=90, fontsize=14)

    # Location labels
    ax.text(-125.6, 48.1, 'Pacific Ocean', fontsize=13)
    ax.text(-123.3, 50.3, 'British Columbia', fontsize=13)
    ax.text(-123.8, 47.8, 'Washington \n State', fontsize=13)

    ax.text(-122.38, 47.68, 'Puget Sound', fontsize=13)
    ax.text(-124.7, 48.47, 'Strait of Juan de Fuca', fontsize=13, rotation=-18)
    ax.text(-123.95, 49.28, 'Strait of \n Georgia', fontsize=13, rotation=-2)

    ax.text(-123.21, 49.4, ' Point\nAtkinson', fontsize=20)
    ax.text(-125.76, 50.05, 'Campbell\n River', fontsize=20)
    ax.text(-123.8, 48.43, 'Victoria', fontsize=20)
    ax.text(-122.7, 48.9, 'Cherry\n Point', fontsize=20)
    ax.text(-124.2, 49, 'Nanaimo', fontsize=20)

    # Figure format
    # Don't shift to PST because we want the date to represent the model run.
    ax.set_title(
        'Marine and Atmospheric Conditions\n {:%A, %B %d, %Y}'
        .format(ssh_ts.time[0]),
        **title_font)
    fig.patch.set_facecolor('#2B3E50')
    axis_colors(ax, 'gray')

    # Citation
    ax.text(0.4, -0.25,
            'Wind vectors averaged over four hours previous to maximum ssh',
            horizontalalignment='left',
            verticalalignment='top',
            transform=ax.transAxes, color='white', fontsize=14)
    ax.text(0.4, -0.29,
            'Modelled winds are from the High Resolution Deterministic '
            'Prediction System\n'
            'of Environment Canada: '
            'https://weather.gc.ca/grib/grib2_HRDPS_HR_e.html.',
            horizontalalignment='left',
            verticalalignment='top',
            transform=ax.transAxes, color='white', fontsize=14)
    ax.text(0.4, -0.35,
            'Pacific North-West coastline was created from '
            'BC Freshwater Atlas Coastline\n and WA Marine Shorelines files '
            'and compiled by Rich Pawlowicz.',
            horizontalalignment='left',
            verticalalignment='top',
            transform=ax.transAxes, color='white', fontsize=14)

    # Information_box
    axs = [ax1, ax2, ax3]
    info_box = ['Point Atkinson', 'Campbell River', 'Victoria']
    for ax, name in zip(axs, info_box):
        plt.setp(list(ax.spines.values()), visible=False)
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        axis_colors(ax, 'blue')

        display_time = arrow.get(max_ssh_time[name]).to('local')

        ax.text(
            0.05, 0.9, name, fontsize=20,
            horizontalalignment='left', verticalalignment='top', color='w')
        ax.text(
            0.05, 0.7, 'Maximum Water Level: {:.1f} m'
            .format(max_ssh[name]), fontsize=15,
            horizontalalignment='left', verticalalignment='top', color='w')
        ax.text(
            0.05, 0.3, 'Time: {time} [{tzone}]'
            .format(time=display_time.format('YYYY-MM-DD HH:mm'),
                    tzone=display_time.tzinfo.tzname(display_time.datetime)),
            fontsize=15,
            horizontalalignment='left', verticalalignment='top', color='w')
        ax.text(
            0.05, 0.5, 'Wind speed: {:.0f} kph'
            .format(unit_conversions.mps_kph(max_windavg[name])), fontsize=15,
            horizontalalignment='left', verticalalignment='top', color='w')
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
